

from django.db import models


class StopManager(models.Manager):

    def external(self, trips_year):
        from doc.transport.models import Route
        EXTERNAL = Route.EXTERNAL
        return self.filter(trips_year=trips_year, route__category=EXTERNAL)


class RouteManager(models.Manager):

    def internal(self, trips_year):
        from doc.transport.models import Route
        return self.filter(trips_year=trips_year, category=Route.INTERNAL)

    def external(self, trips_year):
        from doc.transport.models import Route
        return self.filter(trips_year=trips_year, category=Route.EXTERNAL)


class ScheduledTransportManager(models.Manager):

    def internal(self, trips_year):
        from doc.transport.models import Route
        return self.filter(trips_year=trips_year, route__category=Route.INTERNAL)