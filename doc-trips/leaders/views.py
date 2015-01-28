
import logging
from collections import defaultdict

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponse
from django.db.models import Count
from django.forms import ModelForm
from django import forms

from vanilla import (ListView, CreateView, DetailView, UpdateView, 
                     FormView, RedirectView, TemplateView)
from crispy_forms.layout import Field


from permissions.views import GraderPermissionRequired, LoginRequiredMixin

from leaders.models import LeaderApplication, LeaderGrade
from db.views import *
from db.models import TripsYear
from db.forms import tripsyear_modelform_factory
from timetable.models import Timetable
from leaders.forms import LeaderApplicationFormHelper, LeaderApplicationFormLayout


logger = logging.getLogger(__name__)


class LeaderApplicationDatabaseListView(DatabaseListView):
    model = LeaderApplication
    context_object_name = 'leaderapplications'
    template_name = 'leader/leaderapplication_index.html'


class LeaderApplicationDatabaseUpdateView(DatabaseUpdateView):
    model = LeaderApplication
    # custom template to handle trip assignment
    template_name = 'leader/db_application_update.html'

    # we don't show the user in the form fields because the user is not editable
    fields = ('status', 'assigned_trip', 'class_year', 'gender', 'hinman_box', 'tshirt_size', 'phone', 
              'from_where', 'what_do_you_like_to_study', 'in_goodstanding_with_college', 
              'trippee_confidentiality', 'dietary_restrictions', 'allergen_information',
              'preferred_sections', 'available_sections', 'preferred_triptypes', 
              'available_triptypes', 'trip_preference_comments', 'personal_activities',
              'personal_communities', 'went_on_trip', 'applied_to_trips', 
              'is_in_hanover_this_fall', 'tell_us_about_yourself',
              'comforting_experience', 'best_compliment', 'trip_leader_roles',
              'what_to_change_about_trips', 'leadership_experience', 
              'working_with_difference', 'coleader_qualities', 
              'why_do_you_want_to_be_involved', 'medical_certifications', 
              'relevant_experience', 'cannot_participate_in', 'spring_leader_training_ok', 
              'summer_leader_training_ok', 'express_yourself')


    def get_context_data(self, **kwargs):
        
        context = super(LeaderApplicationDatabaseUpdateView, self).get_context_data(**kwargs)
        preferred_trips = self.object.get_preferred_trips()
        p_dict = defaultdict(list)
        for trip in preferred_trips:
            p_dict[trip.template.triptype.name].append(trip)
        context['preferred_trips'] = list(p_dict.items())
        
        available_trips = self.object.get_available_trips()
        a_dict = defaultdict(list)
        for trip in available_trips:
            a_dict[trip.template.triptype.name].append(trip)
        context['available_trips'] = list(a_dict.items())
        
        return context
        
    
    def get_form_helper(self, form):
        """ 
        Add submit button to form. 

        Different from the usual db/update.html form because
        LeaderApplications cannot be deleted. 
        """

        helper = FormHelper(form)
        # todo move this to extenal layout?
        helper.layout = Layout(
            Field('status'),
            Field('assigned_trip'),
            LeaderApplicationFormLayout(),
        )
        helper.add_input(Submit('submit', 'Update'))
        return helper


class LeaderApplicationDatabaseDetailView(DatabaseDetailView):
    model = LeaderApplication
    template_name = 'leader/leaderapplication_detail.html'
    fields = ('user',) + LeaderApplicationDatabaseUpdateView.fields 

class LeaderApplicationDatabaseAssignmentView(DatabaseDetailView):
    model = LeaderApplication
    fields = LeaderApplicationDatabaseDetailView.fields

    

class LeaderApply(LoginRequiredMixin, CrispyFormMixin, UpdateView):

    model = LeaderApplication
    success_url = reverse_lazy('leader:apply')

    exclude = ['user', 'status', 'assigned_trip']

    def get_template_names(self):
        """
        Only display the application form if the application is open.

        """
        if Timetable.objects.timetable().is_leader_application_available():
            return ['leader/application_form.html']
        else:
            return ['leader/application_not_available.html']

    def get_context_data(self, **kwargs):
        context = super(LeaderApply, self).get_context_data(**kwargs)
        context['timetable'] = Timetable.objects.timetable()
        return context

    def get_object(self):
        """ 
        Return the application for this user.

        If the user has already applied this year, display a form for them to
        edit. Otherwise, display an empty application form. 
        """
        try:
            return self.get_queryset().get(user=self.request.user, 
                                        trips_year=TripsYear.objects.current())
        except self.model.DoesNotExist:
            return None # causes self.object and context[object] to be None

    def get_form_class(self):
        """ Get form, restricting section choices to those of current TripsYear """

        widgets = {
            'preferred_triptypes': forms.CheckboxSelectMultiple,
            'available_triptypes': forms.CheckboxSelectMultiple, 
            'preferred_sections': forms.CheckboxSelectMultiple,
            'available_sections': forms.CheckboxSelectMultiple
        }
        form = tripsyear_modelform_factory(self.model, TripsYear.objects.current(),
                                            exclude=self.exclude, widgets=widgets)
        return form
        
    def get_form_helper(self, form):
        from crispy_forms.layout import Submit, Field
        helper = LeaderApplicationFormHelper(form)
        if self.object:
            submit_text = 'Update'
        else:
            submit_text = 'Submit'
        helper.add_input(Submit('submit', submit_text))
        return helper

    def form_valid(self, form):
        """ Attach creating user and current trips_year to Application. """
        if self.object is None:
            form.instance.user = self.request.user
            form.instance.trips_year = TripsYear.objects.current()
        return super(LeaderApply, self).form_valid(form)
        

class RedirectToNextGradableApplication(GraderPermissionRequired, RedirectView):
    
    # from RedirectView
    permanent = False 
    
    def get_redirect_url(self, *args, **kwargs):
        """ Return the url of the next LeaderApplication that needs grading """
        
        application = LeaderApplication.objects.next_to_grade(self.request.user)
        if not application:
            return reverse('leader:no_application')
        return reverse('leader:grade', kwargs={'pk': application.pk})


class NoApplicationToGrade(GraderPermissionRequired, TemplateView):
    """ Tell user there are no more applications for her to grade """

    template_name = 'leader/no_application.html'


class LeaderGradeForm(ModelForm):
    class Meta:
        model = LeaderGrade
        fields = ['grade', 'comment', 'hard_skills', 'soft_skills']

    helper = FormHelper()
    helper.add_input(Submit('submit', 'Submit Grade'))


# TODO: restrict this to those with grader permissions
class GradeApplication(GraderPermissionRequired, DetailView, FormView):

    """ Grade a LeaderApplication object. 

    The DetailView encapsulates the LeaderApplication, 
    the FormView the grade form. 
    """

    model = LeaderApplication
    template_name = 'leader/grade.html'
    context_object_name = 'leaderapplication'
    # fields of the application which should be graded
    fields_to_grade = ('personal_activities', 'personal_communities', 'went_on_trip',
                       'applied_to_trips', 'is_in_hanover_this_fall', 
                       'tell_us_about_yourself', 'comforting_experience', 
                       'best_compliment', 'trip_leader_roles', 
                       'what_to_change_about_trips', 'leadership_experience', 
                       'working_with_difference', 'coleader_qualities', 
                       'why_do_you_want_to_be_involved', 'medical_certifications', 
                       'relevant_experience', 'express_yourself')

    form_class = LeaderGradeForm
    success_url = reverse_lazy('leader:grade_random')

    def get_context_data(self, **kwargs):
        """ Get context data to render in template.

        Because The DetailView is first in the MRO inheritance tree,
        The super call retrives the LeaderApplication object (saved as context_object      
        Then we manually add the form instance.
        """
        context = super(GradeApplication, self).get_context_data(**kwargs)
        context['fields_to_grade'] = self.fields_to_grade
        context['form'] = self.get_form()
        return context

    def form_valid(self, form):
        """ Attach grader and application to the grade, save grade to database.
        
        Redirects to success_url. 
        """
        grade = form.save(commit=False)
        grade.grader = self.request.user
        grade.leader_application = self.get_object()
        grade.trips_year = TripsYear.objects.current()
        grade.save()

        return super(GradeApplication, self).form_valid(form)





