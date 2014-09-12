import logging

from django.db import models
from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.forms.models import modelform_factory
from django.db import IntegrityError, transaction
from django.core.exceptions import NON_FIELD_ERRORS, ImproperlyConfigured
from vanilla import ListView, UpdateView, CreateView, DeleteView, TemplateView

from db.models import DatabaseModel, Calendar
from db.forms import tripsyear_modelform_factory
from permissions.views import DatabasePermissionRequired, CalendarPermissionRequired

logger = logging.getLogger(__name__)


class DatabaseMixin(DatabasePermissionRequired):
    """ 
    Mixin for database view pages. 

    Filters objects by the trips_year named group in the url, 
    and restricts access to users. If the user is not logged in, redirect 
    the login page. If the user is logged in, but does not have
    database-viewing privileges, display a 403 Forbidden page.

    Plugs into ModelViews. The url is a database url of the form
    /something/{{trips_year}}/something. The ListView will only display 
    objects for the specified trips_year.

    TODO: handle requests for trips_years which are not in the database.
    They should give 404s? This must not mess up ListViews with no results.
    """

    def get_queryset(self):
        """ Get objects for requested trips_year """

        qs = super(DatabaseMixin, self).get_queryset()
        return qs.filter(trips_year=self.kwargs['trips_year'])


    def get_form_class(self):
        """ 
        Restricts the choices in foreignkey form fields to objects with the
        same trips year.

        Because we can't use an F() object in limit_choices_to.

        formfield_callback is responsible for constructing a FormField 
        from a passed ModelField. Our callback intercepts the usual ForeignKey
        implementation, and only lists choices which have trips_year == to 
        the trips_year matched in the url.
        """

        if self.form_class is not None:
            msg = ('Specifying form_class on %s means that ForeignKey querysets will'
                   'contain objects for ALL trips_years. You must explicitly restrict'
                   'the querysets for these fields, or bad things will happen')
            logger.warn(msg % self.__class__.__name__)
            return self.form_class

        if self.model is not None:
            trips_year = self.kwargs['trips_year']
            return tripsyear_modelform_factory(self.model, trips_year,
                                               fields=self.fields)
        
        msg = "'%s' must either define 'form_class' or 'model' " \
            "or CAREFULLY override 'get_form_class()'"
        raise ImproperlyConfigured(msg % self.__class__.__name__)

    def form_valid(self, form):
        """ 
        Called for valid forms - specifically Create and Update
 
        This deals with a corner case of form validation. Uniqueness 
        constraints don't get caught til the object is saved and raises 
        an IntegrityError.

        We catch this error and pass it to form_valid.

        TODO: parse and prettify the error message. Can we look at 
        object._meta.unique_together? Can we make sure it is a uniqueness
        error?
        """
        try:
            with transaction.atomic():
                return super(DatabaseMixin, self).form_valid(form)
        except IntegrityError as e:
            form.errors[NON_FIELD_ERRORS] = form.error_class([e.__cause__])
            return self.form_invalid(form)

    @classmethod
    def urlpattern(cls):
        """ Return the default urlpattern for this view 

        Implemented on subclass, this is just an interface stub
        """
        msg = 'Not implemented. Implement urlpattern() method on {}'
        raise ImproperlyConfigured(msg.format(cls))


class DatabaseListView(DatabaseMixin, ListView):

    def get_template_names(self):
        """ Get the template for the ListView """
        if self.template_name:
            return [self.template_name]
        
        # auto-generate    TODO: use super() conventions?
        template_name = '{}/{}_index.html'.format(
            self.model.get_app_name(), 
            self.model.get_reference_name()
        )
        return [template_name]
    
    @classmethod
    def urlpattern(cls):
        name = '{}_index'.format(cls.model.get_reference_name())
        return url(r'^$', cls.as_view(), name=name)
    

class DatabaseCreateView(DatabaseMixin, CreateView):
    template_name = 'db/create.html'

    @classmethod
    def urlpattern(cls):
        name = '{}_create'.format(cls.model.get_reference_name())
        return url(r'^create$', cls.as_view(), name=name)

    def post(self, request, *args, **kwargs):
        """ 
        Add trips_year to created object.

        This is the vanilla CreateView, verbatim, with the addition
        of the trips_year.
        """
        form = self.get_form(data=request.POST, files=request.FILES)
        form.instance.trips_year_id = self.kwargs['trips_year']
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_success_url(self):
        """ TODO: for now... """
        from db.urls import get_update_url
        return get_update_url(self.object)


class DatabaseUpdateView(DatabaseMixin, UpdateView):
    template_name ='db/update.html'

    @classmethod
    def urlpattern(cls):
        name = '{}_update'.format(cls.model.get_reference_name())
        return url(r'^(?P<pk>[0-9]+)/update', cls.as_view(), name=name)

    def get_success_url(self):
        """ Redirect to same update page for now. """
        from db.urls import get_update_url
        return get_update_url(self.object)
    

class DatabaseDeleteView(DatabaseMixin, DeleteView):
    template_name = 'db/delete.html'

    success_url_pattern = None

    def get_success_url(self):
        """ Helper method for getting the success url based on 
        succes_url_pattern. 

        CreateView and UpdateView use the models get_absolute_url
        to find the success_url. DeleteView cannot do this because the
        target object hsa been deleted.
        """

        if self.success_url_pattern:
            kwargs = {'trips_year': self.kwargs['trips_year']}
            return reverse(self.success_url_pattern, kwargs=kwargs)

        return super(DatabaseDeleteView, self).get_success_url()

    @classmethod
    def urlpattern(cls):
        name = '{}_delete'.format(cls.model.get_reference_name())
        return url(r'^(?P<pk>[0-9]+)/delete', cls.as_view(), name=name)
        

class DatabaseIndexView(DatabaseMixin, TemplateView):
    """ 
    Index page of a particular trips year. 

    TODO: should this display the ScheduledTrips index? 
    """
    
    template_name = 'db/db_index.html'


class DatabaseRedirectView(DatabasePermissionRequired, TemplateView):
    """ 
    Redirect to the trips database for the current year. 

    This view is the target of database urls.

    TODO: implement
    """
    pass
    

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.forms import ModelForm

class CalendarForm(ModelForm):
    
    class Meta:
        model = Calendar

    helper = FormHelper()
    helper.add_input(Submit('submit', 'Change calendar dates'))
    

class CalendarEditView(CalendarPermissionRequired, UpdateView):
    
    model = Calendar
    template_name = 'db/calendar.html'
    
    form_class = CalendarForm

    def get_object(self):
        
        return Calendar.objects.calendar()
        
