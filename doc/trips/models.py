import collections

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError

from doc.db.models import DatabaseModel
from doc.transport.models import Stop, Route
from doc.trips.managers import (SectionDatesManager, SectionManager,
                                ScheduledTripManager)
"""
TODO: use these in place of magic numbers?
INTVL_LEADERS = timedelta(days=0)
INTVL_TRIPPEES = timedelta(days=1)
INTVL_CAMPSITE_1
INTVL_CAMPSITE_2
INTVL_LODGE
INTVL_CAMPUS
"""

NUM_BAGELS_REGULAR = 1.3  # number of bagels per person
NUM_BAGELS_SUPPLEMENT = 1.6  # number of bagels for supplemental trip


class ScheduledTrip(DatabaseModel):

    model_name = 'scheduledtrip'
    objects = ScheduledTripManager()

    template = models.ForeignKey('TripTemplate', on_delete=models.PROTECT)
    section = models.ForeignKey(
        'Section', on_delete=models.PROTECT, related_name='trips'
    )

    # The leaders for this trip can be accessed through the 'leaders' field.
    # See LeaderApplication.assigned_trip.

    # Fields to override the default transport routes. If any of these 
    # routes are set, they are used instead of trip.template.*_route.
    # Is there a way to easily tell when a route is way off for a stop?
    ROUTE_HELP_TEXT = 'leave blank to use default route from template'
    dropoff_route = models.ForeignKey(
        Route, blank=True, null=True, on_delete=models.PROTECT,
        related_name='overridden_dropped_off_trips', help_text=ROUTE_HELP_TEXT)
    pickup_route = models.ForeignKey(
        Route, blank=True, null=True, on_delete=models.PROTECT,
        related_name='overridden_picked_up_trips', help_text=ROUTE_HELP_TEXT)
    return_route =  models.ForeignKey(
        Route, blank=True, null=True, on_delete=models.PROTECT,
        related_name='overriden_returning_trips', help_text=ROUTE_HELP_TEXT)

    class Meta:
        # no two ScheduledTrips can have the same template-section-trips_year
        # combination; we don't want to schedule two identical trips
        unique_together = ('template', 'section', 'trips_year')
        ordering = ('section__name', 'template__name')

    def get_dropoff_route(self):
        """ 
        Returns the overriden dropoff, if set 
        """
        if self.dropoff_route:
            return self.dropoff_route
        return self.template.dropoff.route

    def get_pickup_route(self):
        """ 
        Returns the overriden pickup, if set 
        """
        if self.pickup_route:
            return self.pickup_route
        return self.template.pickup.route

    def get_return_route(self):
        """ 
        Returns the overriden return route, if set 
        """
        if self.return_route:
            return self.return_route
        return self.template.return_route

    def size(self):
        """ 
        Return the number trippees + leaders on this trip 

        HACK: is it safe to cache like this?
        """
        if not hasattr(self, '_size'):
            self._size = self.leaders.count() + self.trippees.count()
        return self._size

    @property 
    def dropoff_date(self):
        return self.section.at_campsite1

    @property
    def pickup_date(self):
        return self.section.arrive_at_lodge

    @property
    def return_date(self):
        return self.section.return_to_campus

    @property
    def half_foodbox(self):
        """ 
        A trip gets an additional half foodbox if it is larger 
        than the kickin limit specified by the triptype.
        """
        return self.size() >= self.template.triptype.half_kickin 

    @property
    def supplemental_foodbox(self):
        """
        Does the trip get a supplemental foodbox?
        """
        return self.template.triptype.gets_supplemental

    @property
    def bagels(self):
        """
        How many bagels does to the trip get?
        """
        if self.supplemental_foodbox:
            num = NUM_BAGELS_SUPPLEMENT
        else:
            num = NUM_BAGELS_REGULAR
        return round(num * self.size())

    def __str__(self):
        return '{}{}'.format(self.section.name, self.template.name)
    
    def verbose_str(self):
        return '{}{}: {}'.format(
            self.section.name, self.template.name,
            self.template.description_summary
        )


class Section(DatabaseModel):
    """ 
    Model to represent a trips section. 
    """

    class Meta:
        ordering = ['name']

    name = models.CharField(
        max_length=1, help_text="A, B, C, etc.", verbose_name='Section'
    )
    leaders_arrive = models.DateField()
    
    is_local = models.BooleanField(default=False)
    is_exchange = models.BooleanField(default=False)
    is_transfer = models.BooleanField(default=False)
    is_international = models.BooleanField(default=False)
    is_fysep = models.BooleanField(default=False)
    is_native = models.BooleanField(default=False)
    
    objects = SectionManager()
    dates = SectionDatesManager()

    @property
    def trippees_arrive(self):
        """ 
        Date that trippees arrive in Hanover.
        """
        return self.leaders_arrive + timedelta(days=1)

    @property
    def at_campsite1(self):
        """ 
        Date that section is at first campsite 
        """
        return self.leaders_arrive + timedelta(days=2)

    @property
    def at_campsite2(self):
        """ 
        Date the section is at the second campsite 
        """
        return self.leaders_arrive + timedelta(days=3)

    @property
    def nights_camping(self):
        """ 
        List of dates when trippees are camping out on the trail.
        """
        return [self.at_campsite1, self.at_campsite2]

    @property
    def arrive_at_lodge(self):
        """ 
        Date section arrives at the lodge. 
        """
        return self.leaders_arrive + timedelta(days=4)

    @property
    def return_to_campus(self):
        """
        Date section returns to campus from the lodge 
        """
        return self.leaders_arrive + timedelta(days=5)

    @property
    def trip_dates(self):
        """ 
        All dates when trippees are here for trips.
        
        Excludes the day leaders arrive.
        """
        return [self.trippees_arrive, self.at_campsite1, self.at_campsite2,
                self.arrive_at_lodge, self.return_to_campus]

    def __str__(self):
        return 'Section ' + self.name
        
    def leader_date_str(self):
        """ 
        Return a string of dates that this section covers.
        
        These are the leader dates.
        Looks like 'Aug 10th to Aug 15th'
        """
        fmt = '%b %d'
        return (self.leaders_arrive.strftime(fmt) + ' to ' + 
                self.return_to_campus.strftime(fmt))

    def trippee_date_str(self):
        """ 
        Date string for *trippees*
        """
        fmt = '%b %d'
        return (self.trippees_arrive.strftime(fmt) + ' to ' + 
                self.return_to_campus.strftime(fmt))



def validate_triptemplate_name(value):
    """ 
    Validator for TripTemplate.name 
    """
    if value < 0 or value > 999:
        raise ValidationError('Value must be in range 0-999')


class TripTemplate(DatabaseModel):

    name = models.PositiveSmallIntegerField(
        db_index=True, validators=[validate_triptemplate_name]
    )
    description_summary = models.CharField("Summary", max_length=255) 

    triptype = models.ForeignKey(
        'TripType', verbose_name='trip type', on_delete=models.PROTECT
    )
    max_trippees = models.PositiveSmallIntegerField()
    non_swimmers_allowed = models.BooleanField(
        "non-swimmers allowed", default=True,
        help_text=(
            "otherwise, trippees on the assignment page will be those who are "
            "at least 'BEGINNER' swimmers"
        )
    )
    dropoff = models.ForeignKey(
        Stop, related_name='dropped_off_trips', on_delete=models.PROTECT)
    pickup = models.ForeignKey(
        Stop, related_name='picked_up_trips', on_delete=models.PROTECT)
    # TODO: remove null=True. All templates need a return route.
    return_route = models.ForeignKey(
        Route, related_name='returning_trips', null=True, on_delete=models.PROTECT)

    # TODO: better related names
    campsite1 = models.ForeignKey(
        'Campsite', related_name='trip_night_1', on_delete=models.PROTECT, 
        verbose_name='campsite 1')
    campsite2 = models.ForeignKey(
        'Campsite', related_name='trip_night_2', on_delete=models.PROTECT, 
        verbose_name='campsite 2')

    description_introduction = models.TextField('Introduction', blank=True)
    description_day1 = models.TextField('Day 1', blank=True)
    description_day2 = models.TextField('Day 2', blank=True)
    description_day3 = models.TextField('Day 3', blank=True)
    description_conclusion = models.TextField('Conclusion', blank=True)
    revision_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    @property
    def max_num_people(self):
        """ 
        Maximum number of people on trip: max_trippees + 2 leaders 
        """
        return self.max_trippees + 2

    def __str__(self):
        return "{}: {}".format(self.name, self.description_summary)


class TripType(DatabaseModel):
    
    name = models.CharField(max_length=255, db_index=True)
    leader_description = models.TextField()
    trippee_description = models.TextField()
    packing_list = models.TextField(blank=True)
    # TODO: the packing list should be inherited, somehow.
    # can we have some sort of common/base packing list? and add in extras?

   # --- foodbox info ----
    half_kickin = models.PositiveSmallIntegerField(
        'minimum # for a half foodbox', default=10
    )
    gets_supplemental = models.BooleanField(
        'gets a supplemental foodbox?', default=False
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Campsite(DatabaseModel):
    
    name = models.CharField(max_length=255)
    capacity = models.PositiveSmallIntegerField(null=True)
    directions = models.TextField()
    bugout = models.TextField() # directions for quick help/escape
    secret = models.TextField() # door codes, hidden things, other secret information

    class Meta:
        ordering = ['name']

    def get_occupancy(self):
        """ 
        Get all ScheduledTrips staying at this campsite
        
        Returns a dictionary of date:list(trips) pairs. 
        """
        
        trips_year = self.trips_year
        camping_dates = Section.dates.camping_dates(trips_year)

        # all trips which stay at campsite
        resident_trips = (
            ScheduledTrip.objects
            .filter(trips_year=trips_year)
            .filter(Q(template__campsite1=self) |
                    Q(template__campsite2=self))
            .select_related('section', 'template')
        )

        # mapping of dates -> trips at this campsite
        trips_by_date = {date: [] for date in camping_dates}

        for trip in resident_trips:
            if trip.template.campsite1 == self:
                trips_by_date[trip.section.at_campsite1].append(trip)
            if trip.template.campsite2 == self:
                trips_by_date[trip.section.at_campsite2].append(trip)

        return trips_by_date

    def get_occupancy_list(self):
        """ List of ScheduledTrips at campsite

        The occupancy has a one-to-one correspondance with 
        Section.dates.camping_dates
        """
        
        occupancy = self.get_occupancy()
        keys = sorted(occupancy.keys())

        def total_occupants(trips):
            total = 0
            for trip in trips: 
                total += trip.template.max_trippees
            return total

        return map(lambda k: (occupancy[k], total_occupants(occupancy[k])), keys)
    
    def __str__(self):
        return self.name
