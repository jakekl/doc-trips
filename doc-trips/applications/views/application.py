
from vanilla import CreateView, UpdateView, RedirectView, TemplateView
from braces.views import FormMessagesMixin
from braces.views import LoginRequiredMixin, PermissionRequiredMixin
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.core.urlresolvers import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.contrib import messages

from db.views import CrispyFormMixin
from db.views import DatabaseListView, DatabaseDetailView, DatabaseUpdateView, DatabaseMixin
from db.models import TripsYear
from db.forms import tripsyear_modelform_factory
from timetable.models import Timetable
from trips.models import TripType
from applications.models import GeneralApplication, LeaderSupplement, CrooSupplement, ApplicationInformation, CrooApplicationGrade, LeaderApplicationGrade
from applications.forms import ApplicationForm, CrooSupplementForm, LeaderSupplementForm, LeaderSupplementAdminForm, CrooApplicationGradeForm
from permissions.views import CreateApplicationsPermissionRequired, CrooGraderPermissionRequired
from utils.views import MultipleFormMixin


class IfApplicationAvailable():

    """ Restrict application availability based on Timetable dates """

    def dispatch(self, request, *args, **kwargs):
        if Timetable.objects.timetable().applications_available():
            return super(IfApplicationAvailable, self).dispatch(request, *args, **kwargs)
        
        return render(request, 'applications/not_available.html')


class ContinueIfAlreadyApplied():
    """ 
    If user has already applied, redirect to edit existing application.
    
    This lives in a mixin instead of in the NewApplication view because if
    has to follow LoginRequired in the MRO. An AnonymousUser causes the 
    query to throw an error.
    """

    def dispatch(self, request, *args, **kwargs):

        if self.model.objects.filter(applicant=self.request.user, 
                                     trips_year=TripsYear.objects.current().year).exists():
            return HttpResponseRedirect(reverse('applications:continue'))

        return super(ContinueIfAlreadyApplied, self).dispatch(request, *args, **kwargs)


class ApplicationFormsMixin(FormMessagesMixin, MultipleFormMixin, CrispyFormMixin):

    model = GeneralApplication
    template_name = 'applications/application.html'

    form_valid_message = "Your application has been saved"
    form_invalid_message = "Uh oh. Looks like there's a problem somewhere in your application"

    def get_form_classes(self):

        return {
            'form': ApplicationForm,
            'leader_form': LeaderSupplementForm,
            'croo_form': CrooSupplementForm,
        }

    def get_context_data(self, **kwargs):
        """ Lots o' goodies for the template """

        trips_year = TripsYear.objects.current()
        return super(ApplicationFormsMixin, self).get_context_data(
            trips_year=trips_year,
            timetable=Timetable.objects.timetable(),
            information=ApplicationInformation.objects.get(trips_year=trips_year),
            triptypes=TripType.objects.filter(trips_year=trips_year),
            **kwargs
        )
    

class NewApplication(LoginRequiredMixin, IfApplicationAvailable, 
                     ContinueIfAlreadyApplied, ApplicationFormsMixin, CreateView):
                     
    success_url = reverse_lazy('applications:continue')

    def form_valid(self, forms):
        """ Connect the application instances """
        
        trips_year = TripsYear.objects.current()
        forms['form'].instance.applicant = self.request.user
        forms['form'].instance.trips_year = trips_year
        # form.status??
        application = forms['form'].save()

        forms['leader_form'].instance.application = application
        forms['leader_form'].instance.trips_year = trips_year
        forms['leader_form'].save()

        forms['croo_form'].instance.application = application
        forms['croo_form'].instance.trips_year = trips_year
        forms['croo_form'].save()

        return HttpResponseRedirect(self.get_success_url())


class ContinueApplication(LoginRequiredMixin, IfApplicationAvailable,  
                          ApplicationFormsMixin, UpdateView):
    """ 
    View to edit applications, for applicants.
    """
    success_url = reverse_lazy('applications:continue')
    context_object_name = 'application'
    
    def get_object(self):
        """ TODO: perhaps redirect to NewApplication instead of 404? """
        return get_object_or_404(self.model, 
                                 applicant=self.request.user,
                                 trips_year=TripsYear.objects.current())

    def get_instances(self):

        self.object = self.get_object()
        return {
            'form': self.object,
            'leader_form': self.object.leader_supplement,
            'croo_form': self.object.croo_supplement,
        }

    
class SetupApplication(CreateApplicationsPermissionRequired, 
                       CrispyFormMixin, UpdateView):
    """
    Create/edit this year's application

    Used by directors to edit application questions, general information.

    TOOD: show previous year's application documents??? 
    """

    model = ApplicationInformation
    template_name = 'applications/setup.html'
    success_url = reverse_lazy('applications:setup')

    def get_object(self):
        """ There is only one configuration object for each trips year. """
        trips_year = TripsYear.objects.current()
        obj, created = self.model.objects.get_or_create(trips_year=trips_year)
        
        return obj

    def get_form(self, **kwargs):

        form = super(SetupApplication, self).get_form(**kwargs)
        form.helper = FormHelper(form)
        form.helper.add_input(Submit('submit', 'Update'))

        return form

    def get_context_data(self, **kwargs):
        """ Add current tripsyear to template context """
        context = super(SetupApplication, self).get_context_data(**kwargs)
        context['trips_year'] = TripsYear.objects.current()
        return context


class ApplicationDatabaseListView(DatabaseListView):
    model = GeneralApplication
    context_object_name = 'applications'
    template_name = 'applications/application_index.html'


class LeaderApplicationDatabaseListView(DatabaseListView):
    model = LeaderSupplement
    context_object_name = 'applications'
    template_name = 'applications/leaderapplication_index.html'

    def get_queryset(self):
        return self.model.objects.completed_applications(self.kwargs['trips_year'])


class LeaderApplicationDatabaseDetailView(DatabaseDetailView):
    model = LeaderSupplement
    template_name = 'applications/leaderapplication_detail.html'
    fields = ('trip_preference_comments', 'cannot_participate_in')


class LeaderApplicationAdminDatabaseUpdateView(DatabaseUpdateView):
    """ Edit admin data - trainings, application status """
    model = LeaderSupplement
    form_class = LeaderSupplementAdminForm
    template_name = 'applications/leaderapplication_admin_update.html'


class ApplicationDatabaseUpdateView(DatabaseMixin, ApplicationFormsMixin, 
                                    UpdateView):
    
    # TODO : debug, pull applications from kwargs.
    
    template_name = 'applications/application_update.html'
    context_object_name = 'application'

    def get_instances(self):

        self.object = self.get_object()
        return {
            'form': self.object,
            'leader_form': self.object.leader_supplement,
            'croo_form': self.object.croo_supplement,
        }


    def get_context_data(self, **kwargs):
        """ Override ApplicationFormsMixin get_context_data """
        trips_year = self.kwargs['trips_year']
        return super(ApplicationFormsMixin, self).get_context_data(
            trips_year=trips_year,
            information=ApplicationInformation.objects.get(trips_year=trips_year),
            triptypes=TripType.objects.filter(trips_year=trips_year),
            **kwargs
        )    
        
