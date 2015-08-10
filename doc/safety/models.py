from django.conf import settings
from django.db import models
from django.core.urlresolvers import reverse

from doc.db.models import DatabaseModel
from doc.trips.models import Trip

"""
Models for Incident Reports
"""

def YesNoField(*args, **kwargs):
    kwargs['choices'] = (
        (True, 'Yes'), (False, 'No')
    )
    kwargs['default'] = False
    return models.BooleanField(*args, **kwargs)


ROLE_CHOICES = (
    ('TRIP_LEADER', 'Trip Leader'),
    ('CROO_MEMBER', 'Croo Member'),
    ('TRIPPEE', 'Trippee'),
    ('OTHER', 'Other')
)

class _IncidentBase(DatabaseModel):
    """ 
    Base fields for Incident and IncidentUpdate
    """
    class Meta:
        abstract = True

    # inputing user
    user = models.ForeignKey(settings.AUTH_USER_MODEL, editable=False)
    user_role = models.CharField(
        'What is your role on Trips?', choices=ROLE_CHOICES, max_length=20
    )
    created = models.DateTimeField(auto_now_add=True, editable=False)

    caller = models.CharField("Who called?", max_length=255)
    caller_role = models.CharField(choices=ROLE_CHOICES, max_length=20)
    # TODO fill in other
    caller_number = models.CharField(max_length=20)  # phone number


class Incident(_IncidentBase):

    trip = models.ForeignKey(
        Trip, verbose_name='On what trip did this incident occur?'
    )
    where = models.TextField(
        "Where during the trip did this occur?",
        help_text="trail name, campsite, Hanover, Lodge, etc"
    )
    when = models.DateTimeField("When did this incident occur?")

    injuries = YesNoField('Did any injuries take place during this incident?')
    subject = models.CharField("Who did this happen to?", blank=True, max_length=255)
    subject_role = models.CharField(choices=ROLE_CHOICES, blank=True, max_length=20)
    # TODO fill in other

    desc = models.TextField('Describe the incident')
    resp = models.TextField('What was the response to the incident?')
    outcome = models.TextField('What was the outcome of the response?')
  
    follow_up = models.TextField(
        'Is any additional follow-up needed? If so, what?'
    )

    # TODO: closed? resolved?
    
    def detail_url(self):
        return reverse('db:safety:detail', kwargs=self.obj_kwargs())

    def __str__(self):
        return "%s: %s" % (self.trip, self.when)


class IncidentUpdate(_IncidentBase):
    incident = models.ForeignKey(Incident, editable=False)  # parent
    update = models.TextField()

    class Meta:
        ordering = ['created']