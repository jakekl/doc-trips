
from collections import namedtuple

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Row, Div
import django_filters
from django.db.models import Q

from fyt.applications.models import GeneralApplication, QualificationTag
from fyt.trips.models import Section, TripType

CROO_QUALIFICATIONS = 'croo_supplement__grades__qualifications'
AVAILABLE_SECTIONS = 'available_sections'
AVAILABLE_TRIPTYPES = 'available_triptypes'


class AvailableSectionFilter(django_filters.ModelChoiceFilter):
    """Filter leaders based on the trips sections they are available for."""
    def __init__(self, trips_year):
        qs = Section.objects.filter(trips_year=trips_year)
        super().__init__(queryset=qs)

    def filter(self, qs, value):
        if not value:
            return qs

        return qs.filter(
            Q(leader_supplement__preferred_sections=value) |
            Q(leader_supplement__available_sections=value))


class AvailableTripTypeFilter(django_filters.ModelChoiceFilter):
    """Filter leaders based on the trip types they are available for."""
    def __init__(self, trips_year):
        qs = TripType.objects.filter(trips_year=trips_year)
        super().__init__(queryset=qs)

    def filter(self, qs, value):
        if not value:
            return qs

        return qs.filter(
            Q(leader_supplement__preferred_triptypes=value) |
            Q(leader_supplement__available_triptypes=value))


_Choice = namedtuple('_Choice', ['value', 'display', 'action'])

class ApplicationTypeFilter(django_filters.ChoiceFilter):
    """Filter for different types of applications."""
    def __init__(self, *args, **kwargs):
        choices = list(map(lambda c: _Choice(*c), self.choices))
        filter_choices = map(lambda c: (c.value, c.display), choices)
        self.actions = dict(map(lambda c: (c.value, c.action), choices))
        super().__init__(self, *args, choices=filter_choices, **kwargs)

    # (query_value, display value, method)
    choices = [
        ('any', 'All Applications', None),
        ('croo', 'Croo Applications', 'croo_applications'),
        ('leader', 'Leader Applications', 'leader_applications'),
        ('either', 'Leader OR Croo Applications', 'either_applications'),
        ('both', 'Leader AND Croo Applications', 'both_applications'),
    ]

    def croo_applications(self, qs):
        return qs.exclude(croo_supplement__document='')

    def leader_applications(self, qs):
        return qs.exclude(leader_supplement__document='')

    def either_applications(self, qs):
        return qs.exclude(Q(leader_supplement__document='') &
                          Q(croo_supplement__document=''))

    def both_applications(self, qs):
        return qs.exclude(Q(leader_supplement__document='') |
                          Q(croo_supplement__document=''))

    def filter(self, qs, value):
        if not value or not self.actions[value]:
            return qs

        action = getattr(self, self.actions[value])
        if not action:
            return qs

        return action(qs)


class CrooQualificationFilter(django_filters.ModelMultipleChoiceFilter):
    """Filter croo leaders based on recommended qualifications."""
    def __init__(self, trips_year):
        qs = QualificationTag.objects.filter(trips_year=trips_year)
        super().__init__(name=CROO_QUALIFICATIONS,
                         label='Croo Qualifications',
                         queryset=qs)
        # TODO: this causes a HUGE number of queries. WHY?
        # widget=forms.CheckboxSelectMultiple()


class ApplicationFilterSet(django_filters.FilterSet):

    class Meta:
        model = GeneralApplication
        fields = ['status']

    name = django_filters.MethodFilter(action='lookup_user_by_name')
    netid = django_filters.MethodFilter(action='lookup_user_by_netid')
    complete = ApplicationTypeFilter()  # not associated with a specific field

    def lookup_user_by_name(self, qs, value):
        if not value:
            return qs

        return qs.filter(applicant__name__icontains=value)

    def lookup_user_by_netid(self, qs, value):
        if not value:
            return qs

        return qs.filter(applicant__netid__iexact=value)

    def __init__(self, *args, **kwargs):
        trips_year = kwargs.pop('trips_year')
        super().__init__(*args, **kwargs)

        # add a blank choice
        self.filters['status'].field.choices.insert(0, ('', 'Any'))
        self.filters['status'].field.label = 'Status'

        self.filters[CROO_QUALIFICATIONS] = CrooQualificationFilter(trips_year)
        self.filters[AVAILABLE_SECTIONS] = AvailableSectionFilter(trips_year)
        self.filters[AVAILABLE_TRIPTYPES] = AvailableTripTypeFilter(trips_year)

        # Remove 'Filter' help text
        for filter in self.filters.values():
            filter.field.help_text = ""

        self.form.helper = FilterSetFormHelper(self.form)


class FilterSetFormHelper(FormHelper):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def filter_row(filter):
            return Row(Div(filter, css_class='col-lg-12'))

        self.form_method = 'GET'
        self.layout = Layout(
            filter_row('complete'),
            filter_row('status'),
            filter_row('name'),
            filter_row('netid'),
            filter_row(AVAILABLE_SECTIONS),
            filter_row(AVAILABLE_TRIPTYPES),
            filter_row(CROO_QUALIFICATIONS),
            filter_row(Submit('submit', 'Filter', css_class='btn-block'))
        )
