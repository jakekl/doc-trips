from django.conf.urls import url

from doc.reports.views import (
    VolunteerCSV, TripLeaderApplicationsCSV, CrooApplicationsCSV, 
    FinancialAidCSV, ExternalBusCSV, Charges
)

urlpatterns = [
    url(r'^applications/all/$', VolunteerCSV.as_view(), name='all_apps'),
    url(r'^applications/trip-leaders/$', TripLeaderApplicationsCSV.as_view(), 
        name='trip_leader_apps'),
    url(r'^applications/croos/$', CrooApplicationsCSV.as_view(),
        name='croo_apps'),
    url(r'^registrations/financial-aid/$', FinancialAidCSV.as_view(),
        name='financial_aid'),
    url(r'^registrations/bus-stops/$', ExternalBusCSV.as_view(),
        name='bus_stops'),
    url(r'^incoming/charges/$', Charges.as_view(), name="charges"),
]
