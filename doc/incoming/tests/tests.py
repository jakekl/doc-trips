import os
import unittest

from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from model_mommy import mommy

from doc.test.fixtures import TripsYearTestCase, WebTestCase
from doc.incoming.models import Registration, IncomingStudent
from doc.trips.models import ScheduledTrip

class IncomingStudentModelsTestCase(TripsYearTestCase):

    
    def test_creating_Registration_automatically_links_to_existing_IncomingStudent(self):
        
        user = self.mock_incoming_student()
        trips_year = self.init_current_trips_year()
        # make existing info for user with netid
        incoming = mommy.make(IncomingStudent, netid=user.netid, trips_year=trips_year)
        
        reg = mommy.make(Registration, trips_year=trips_year, user=user)
        self.assertEqual(reg.trippee, incoming)

    def test_creating_Registration_without_incoming_info_does_nothing(self):
 
        user = self.mock_incoming_student()
        trips_year = self.init_current_trips_year()
        
        reg = mommy.make(Registration, trips_year=trips_year, user=user)

        with self.assertRaises(ObjectDoesNotExist):
            reg.trippee


    def test_creating_IncomingStudent_connects_to_existing_registration(self):
        
        user = self.mock_incoming_student()
        trips_year = self.init_current_trips_year()
        reg = mommy.make(Registration, trips_year=trips_year, user=user)

        incoming = mommy.make(IncomingStudent, netid=user.netid, trips_year=trips_year)
        # refresh registration
        reg = Registration.objects.get(pk=reg.pk)
        
        self.assertEqual(incoming.registration, reg) 


class RegistrationModelTestCase(TripsYearTestCase):

    def test_get_trip_assignment_returns_assignment(self):
        trips_year = self.init_current_trips_year()
        trip = mommy.make(ScheduledTrip, trips_year=trips_year)
        reg = mommy.make(Registration, trips_year=trips_year)
        trippee = mommy.make(IncomingStudent, trips_year=trips_year, trip_assignment=trip, registration=reg)
        self.assertEqual(trip, reg.get_trip_assignment())

    def test_get_trip_assignment_with_no_assigned_trip_returns_None(self):
        trips_year = self.init_current_trips_year()
        reg = mommy.make(Registration, trips_year=trips_year)
        trippee = mommy.make(IncomingStudent, trips_year=trips_year, trip_assignment=None, registration=reg)
        self.assertIsNone(reg.get_trip_assignment())

    def test_get_trip_assignment_with_no_IncomingStudent_returns_None(self):
        trips_year = self.init_current_trips_year()
        reg = mommy.make(Registration, trips_year=trips_year)
        self.assertIsNone(reg.get_trip_assignment())

    def test_nonswimmer_property(self):
        trips_year = self.init_current_trips_year()
        non_swimmer =  mommy.make(Registration, trips_year=trips_year, swimming_ability=Registration.NON_SWIMMER)
        self.assertTrue(non_swimmer.is_non_swimmer)
        for choice in [Registration.BEGINNER, Registration.COMPETENT, Registration.EXPERT]:
            swimmer = mommy.make(Registration, trips_year=trips_year, swimming_ability=choice)
            self.assertFalse(swimmer.is_non_swimmer)

    def test_base_trip_choice_queryset_filters_for_nonswimmers(self):
        trips_year = self.init_current_trips_year()
        trip1 = mommy.make(ScheduledTrip, trips_year=trips_year, template__non_swimmers_allowed=False)
        trip2 = mommy.make(ScheduledTrip, trips_year=trips_year, template__non_swimmers_allowed=True)
        reg = mommy.make(Registration, trips_year=trips_year, swimming_ability=Registration.NON_SWIMMER,
                         preferred_sections=[trip1.section, trip2.section])
        self.assertEqual(list(reg._base_trips_qs()), [trip2])

    def test_base_trips_qs_filters_for_preferred_and_available_sections(self):
        trips_year = self.init_current_trips_year()
        trip1 = mommy.make(ScheduledTrip, trips_year=trips_year)
        trip2 = mommy.make(ScheduledTrip, trips_year=trips_year)
        trip3 = mommy.make(ScheduledTrip, trips_year=trips_year)
        reg = mommy.make(Registration, trips_year=trips_year, swimming_ability=Registration.COMPETENT,
                         preferred_sections=[trip1.section], available_sections=[trip2.section])
        self.assertEqual(set(reg._base_trips_qs()), set([trip1, trip2]))

    def test_get_firstchoice_trips(self):
        trips_year = self.init_current_trips_year()
        section1 = mommy.make('Section', trips_year=trips_year)
        section2 = mommy.make('Section', trips_year=trips_year)
        firstchoice_triptype = mommy.make('TripType', trips_year=trips_year)
        trip1 = mommy.make(ScheduledTrip, trips_year=trips_year, section=section1, template__triptype=firstchoice_triptype)
        trip2 = mommy.make(ScheduledTrip, trips_year=trips_year, section=section2, template__triptype=firstchoice_triptype)
        reg = mommy.make(Registration, trips_year=trips_year,
                         firstchoice_triptype=firstchoice_triptype,
                         swimming_ability=Registration.COMPETENT,
                         available_sections=[section1])
        self.assertEqual([trip1], list(reg.get_firstchoice_trips()))

    def test_get_preferred_trips(self):

        trips_year = self.init_current_trips_year()
        section1 = mommy.make('Section', trips_year=trips_year)
        section2 = mommy.make('Section', trips_year=trips_year)
        triptype = mommy.make('TripType', trips_year=trips_year)
        trip1 = mommy.make(ScheduledTrip, trips_year=trips_year, section=section1, template__triptype=triptype)
        trip2 = mommy.make(ScheduledTrip, trips_year=trips_year, section=section2, template__triptype=triptype)
        trip3 = mommy.make(ScheduledTrip, trips_year=trips_year, section=section1)
        reg = mommy.make(Registration, trips_year=trips_year,
                         preferred_triptypes=[triptype],
                         swimming_ability=Registration.COMPETENT,
                         preferred_sections=[section1])
        self.assertEqual([trip1], list(reg.get_preferred_trips()))

    def test_get_available_trips(self):

        trips_year = self.init_current_trips_year()
        section1 = mommy.make('Section', trips_year=trips_year)
        section2 = mommy.make('Section', trips_year=trips_year)
        triptype = mommy.make('TripType', trips_year=trips_year)
        trip1 = mommy.make(ScheduledTrip, trips_year=trips_year, section=section1, template__triptype=triptype)
        trip2 = mommy.make(ScheduledTrip, trips_year=trips_year, section=section2, template__triptype=triptype)
        trip3 = mommy.make(ScheduledTrip, trips_year=trips_year, section=section1)
        reg = mommy.make(Registration, trips_year=trips_year,
                         available_triptypes=[triptype],
                         swimming_ability=Registration.COMPETENT,
                         preferred_sections=[section1],
                         available_sections=[section1])
        self.assertEqual([trip1], list(reg.get_available_trips()))

    def test_get_incoming_student(self):
        trips_year = self.init_current_trips_year()
        reg = mommy.make(Registration, trips_year=trips_year)
        self.assertIsNone(reg.get_incoming_student())
        incoming = mommy.make(IncomingStudent, trips_year=trips_year, 
                              registration=reg)
        reg = Registration.objects.get(pk=reg.pk)
        self.assertEqual(reg.get_incoming_student(), incoming)


def resolve_path(fname):
    return os.path.join(os.path.dirname(__file__), fname)

FILE = resolve_path('incoming_students.csv')
FILE_WITH_BLANKS = resolve_path('incoming_students_with_blank_id.csv')


class ImportIncomingStudentsTestCase(TripsYearTestCase):
    
    def test_create_from_csv(self):
        trips_year = self.init_current_trips_year().pk
        with open(FILE) as f:
            (created, existing) = IncomingStudent.objects.create_from_csv_file(f, trips_year)
        self.assertEqual(set(['id_1', 'id_2']), set(created))
        self.assertEqual(existing, [])
        # are student objects created?
        IncomingStudent.objects.get(netid='id_1')
        IncomingStudent.objects.get(netid='id_2')

    def test_ignore_existing_students(self):
        trips_year = self.init_current_trips_year().pk
        with open(FILE) as f:
            (created, existing) = IncomingStudent.objects.create_from_csv_file(f, trips_year)
        with open(FILE) as f:
            (created, existing) = IncomingStudent.objects.create_from_csv_file(f, trips_year)
        self.assertEqual(set(['id_1', 'id_2']), set(existing))
        self.assertEqual(created, [])

    def test_ignore_rows_without_id(self):
        trips_year = self.init_current_trips_year().pk

        with open(FILE_WITH_BLANKS) as f:
            (created, existing) = IncomingStudent.objects.create_from_csv_file(f, trips_year)

        self.assertEqual(set(['id_1']), set(created))
        self.assertEqual(existing, [])
        # are student objects created?
        IncomingStudent.objects.get(netid='id_1')


class RegistrationViewsTestCase(WebTestCase):

    def test_registration_with_anonymous_user(self):
        self.init_current_trips_year()
        self.app.get(reverse('incoming:register'))
