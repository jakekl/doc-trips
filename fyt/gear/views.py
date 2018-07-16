from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.utils.functional import cached_property

from .forms import GearRequestForm
from .models import Gear, GearRequest

from fyt.core.models import TripsYear
from fyt.core.views import (
    BaseCreateView,
    DatabaseCreateView,
    DatabaseDetailView,
    DatabaseListView,
    DatabaseUpdateView,
)


class GearList(DatabaseListView):
    model = Gear


class GearCreate(DatabaseCreateView):
    model = Gear

    def get_headline(self):
        return "Add a new piece of gear"

    def get_success_url(self):
        return reverse('core:gear:list', kwargs=self.kwargs)


class GearUpdate(DatabaseUpdateView):
    model = Gear
    delete_button = False

    def get_success_url(self):
        return reverse('core:gear:list', kwargs={'trips_year': self.trips_year})


class GearRequestList(DatabaseListView):
    model = GearRequest

    def extra_context(self):
        return {
            'matrix': GearRequest.objects.matrix(self.trips_year)
        }


class RequestGear(LoginRequiredMixin, BaseCreateView):
    model = GearRequest
    form_class = GearRequestForm
    template_name = 'form.html'

    @cached_property
    def trips_year(self):
        return TripsYear.objects.current()

    def get_form(self, **kwargs):
        return super().get_form(user=self.request.user, **kwargs)

    def get_headline(self):
        return 'Request Gear'

    def get_success_url(self):
        return self.request.path
