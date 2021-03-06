from braces.views import SetHeadlineMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from vanilla import CreateView, DetailView, FormView, ListView

from fyt.core.views import DatabaseDeleteView, DatabaseUpdateView, TripsYearMixin
from fyt.raids.forms import CommentForm
from fyt.raids.models import Raid, RaidInfo
from fyt.trips.models import Trip
from fyt.utils.forms import crispify
from fyt.utils.views import PopulateMixin


class _RaidMixin(LoginRequiredMixin, TripsYearMixin):
    pass


class RaidHome(TripsYearMixin, DetailView):
    model = RaidInfo
    template_name = 'raids/home.html'

    def get_object(self):
        return self.model.objects.get(trips_year=self.trips_year)


class RaidList(_RaidMixin, ListView):
    model = Raid
    template_name = 'raids/list.html'
    context_object_name = 'raids'

    def get_queryset(self):
        qs = super().get_queryset()
        return (
            qs.annotate(num_comments=Count('comment'))
            .select_related('trip__template', 'trip__section')
            .prefetch_related('user', 'trip__leaders__applicant')
        )


class TripsToRaid(_RaidMixin, ListView):
    model = Trip
    template_name = 'raids/trips.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related(
            'template__campsite1', 'template__campsite2', 'template__description'
        ).prefetch_related('raid_set', 'raid_set__user', 'leaders__applicant')


class RaidTrip(_RaidMixin, PopulateMixin, SetHeadlineMixin, CreateView):
    model = Raid
    fields = ['trip', 'date', 'plan']

    def get_headline(self):
        return mark_safe("New Raid <small> %s </small>" % self.request.user)

    def get_form(self, **kwargs):
        return crispify(super().get_form(**kwargs))

    def form_valid(self, form):
        form.instance.trips_year = self.trips_year
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.detail_url()


class RaidDetail(_RaidMixin, FormView, DetailView):
    model = Raid
    form_class = CommentForm
    template_name = 'raids/raid_detail.html'
    context_object_name = 'raid'

    def get_context_data(self, **kwargs):
        kwargs[self.get_context_object_name()] = self.get_object()
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        form.instance.trips_year = self.trips_year
        form.instance.user = self.request.user
        form.instance.raid = self.get_object()
        form.save()
        return HttpResponseRedirect(self.request.path)


class RaidDelete(DatabaseDeleteView):
    model = Raid
    success_url_pattern = 'core:raids:list'

    def get_headline(self):
        return "Delete %s's raid of %s?" % (self.object.user, self.object.verbose_str())


class UpdateRaidInfo(DatabaseUpdateView):
    model = RaidInfo
    delete_button = False

    def get_object(self):
        return self.model.objects.get(trips_year=self.trips_year)

    def get_success_url(self):
        return reverse('core:raids:home', kwargs=self.kwargs)
