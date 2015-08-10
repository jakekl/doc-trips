
from django import forms
from crispy_forms.layout import Submit, Layout, Field, Submit, Row, Div, HTML, Fieldset
from crispy_forms.helper import FormHelper
from bootstrap3_datetime.widgets import DateTimePicker

from doc.trips.models import Trip
from doc.safety.models import Incident, IncidentUpdate


class IncidentForm(forms.ModelForm):

    class Meta:
        model = Incident
        fields = [
            'user_role',
            'trip',
            'where',
            'when',
            'caller',
            'caller_role',
            'caller_number',
            'injuries',
            'subject',
            'subject_role',
            'desc',
            'resp',
            'outcome',
            'follow_up',
        ]
        widgets = {
            'when': DateTimePicker(options={'format': 'MM/DD/YYYY HH:mm'})
        }

    def __init__(self, trips_year, *args, **kwargs):
        super(IncidentForm, self).__init__(*args, **kwargs)
        self.fields['trip'].queryset = Trip.objects.filter(trips_year=trips_year)

        self.helper = FormHelper()
        self.helper.layout = IncidentFormLayout()


IncidentFormLayout = lambda: Layout(
    HTML('<p><strong> Your are logged in as {{ user }} </strong></p>'),
    'user_role',
    'trip',
    Field('where', rows=2),
    Row(
        Div('when', css_class='col-sm-4')
    ),
    Row(
        Div('caller', css_class='col-sm-3'),
        Div('caller_role', css_class='col-sm-3'),
        Div('caller_number', css_class='col-sm-3'),
    ),
    Row(
        Div('injuries', css_class='col-sm-6'),
    ),
    Row(
        Div('subject', css_class='col-sm-3'),
        Div('subject_role', css_class='col-sm-3'),
    ),
    Field('desc', rows=3),
    Field('resp', rows=3),
    Field('outcome', rows=3),
    Field('follow_up', rows=3),
    Submit('submit', 'Report'),
)


IncidentUpdateFormLayout = lambda: Layout(
    Fieldset(
        'Update the incident (logged in as {{ user }})',
        'user_role',
        Row(
            Div('caller', css_class='col-sm-3'),
            Div('caller_role', css_class='col-sm-3'),
            Div('caller_number', css_class='col-sm-3'),
        ),
        Field('update', rows=4),
    ),
    Submit('submit', 'Update')
)


class IncidentUpdateForm(forms.ModelForm):

    class Meta:
        model = IncidentUpdate

    helper = FormHelper()
    helper.layout = IncidentUpdateFormLayout()