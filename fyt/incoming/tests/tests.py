import os
import unittest
from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.forms.models import model_to_dict
from model_mommy import mommy

from fyt.test.testcases import TripsYearTestCase, WebTestCase
from fyt.incoming.models import Registration, IncomingStudent, sort_by_lastname
from fyt.incoming.forms import RegistrationForm
from fyt.trips.models import Trip, TripType, Section
from fyt.incoming.models import Settings
from fyt.timetable.models import Timetable
from fyt.transport.models import Stop, Route
from fyt.utils.choices import YES, NO
from fyt.users.models import DartmouthUser

class IncomingStudentModelTestCase(TripsYearTestCase):

    
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

    def test_get_hometown_parsing(self):
        trips_year = self.init_trips_year()
        with open(FILE) as f:
            IncomingStudent.objects.create_from_csv_file(f, trips_year.pk)
        incoming = IncomingStudent.objects.get(netid='id_2')
        self.assertEqual(incoming.get_hometown(), 'Chapel Hill, NC USA')
        
    def test_get_hometown_parsing_with_bad_formatting(self):
        trips_year = self.init_trips_year()
        incoming = mommy.make(
            IncomingStudent, trips_year=trips_year, address='what\nblah'
        )
        self.assertEqual(incoming.get_hometown(), 'what\nblah')

    def test_get_gender_without_registration(self):
        trips_year = self.init_trips_year()
        incoming = mommy.make(IncomingStudent, trips_year=trips_year, gender='MALE')
        self.assertEqual(incoming.get_gender(), 'male')
        
    def test_get_gender_with_registration(self):
        """ Pull from registration, if available """
        trips_year = self.init_trips_year()
        reg = mommy.make(Registration, trips_year=trips_year, gender='FEMALE')
        incoming = mommy.make(IncomingStudent, trips_year=trips_year,
                              gender='MALE', registration=reg)
        self.assertEqual(incoming.get_gender(), 'female')

    def test_financial_aid_in_range_0_to_100(self):
        trips_year=self.init_trips_year()
        with self.assertRaises(ValidationError):
            mommy.make(
                IncomingStudent, trips_year=trips_year, 
                financial_aid=-1
            ).full_clean()
        with self.assertRaises(ValidationError):
            mommy.prepare(
                IncomingStudent, trips_year=trips_year, 
                financial_aid=101
            ).full_clean()
        mommy.prepare(
            IncomingStudent, trips_year=trips_year,
            financial_aid=100
        ).full_clean()

    def test_compute_base_cost(self):
        trips_year = self.init_trips_year()
        mommy.make(Settings, trips_year=trips_year, trips_cost=100)
        inc = mommy.make(
            IncomingStudent, trips_year=trips_year,
            trip_assignment=mommy.make(Trip),
            financial_aid=0, bus_assignment_round_trip=None
        )
        self.assertEqual(inc.compute_cost(), 100)

    def test_compute_cost_with_financial_aid(self):
        trips_year = self.init_trips_year()
        mommy.make(Settings, trips_year=trips_year, trips_cost=100)
        inc = mommy.make(
            IncomingStudent, trips_year=trips_year, 
            trip_assignment=mommy.make(Trip),
            financial_aid=35, bus_assignment_round_trip=None
        )
        self.assertEqual(inc.compute_cost(), 65)

    def test_compute_cost_with_bus(self):
        trips_year = self.init_trips_year()
        mommy.make(Settings, trips_year=trips_year, trips_cost=100)
        inc = mommy.make(
            IncomingStudent, trips_year=trips_year, 
            trip_assignment=mommy.make(Trip),
            financial_aid=25, bus_assignment_round_trip__cost_round_trip=25
        )
        self.assertEqual(inc.compute_cost(), 93.75)

    def test_compute_cost_with_doc_membership(self):
        trips_year = self.init_trips_year()
        mommy.make(Settings, trips_year=trips_year, trips_cost=100, doc_membership_cost=50)
        inc = mommy.make(
            IncomingStudent, trips_year=trips_year,
            trip_assignment=mommy.make(Trip),
            financial_aid=25, bus_assignment_round_trip__cost_round_trip=25,
            registration__doc_membership=YES
        )
        self.assertEqual(inc.compute_cost(), 131.25)

    def test_compute_cost_with_green_fund_contribution(self):
        trips_year = self.init_trips_year()
        mommy.make(Settings, trips_year=trips_year, trips_cost=100, doc_membership_cost=50)
        inc = mommy.make(
            IncomingStudent, trips_year=trips_year, 
            trip_assignment=mommy.make(Trip),
            financial_aid=25, bus_assignment_round_trip__cost_round_trip=25,
            registration__doc_membership=YES,
            registration__green_fund_donation=290
        )
        self.assertEqual(inc.compute_cost(), 421.25)

    def test_compute_cost_with_no_trip_assignment_but_with_doc_membership(self):
        trips_year = self.init_trips_year()
        mommy.make(Settings, trips_year=trips_year, trips_cost=100, doc_membership_cost=50)
        inc = mommy.make(
            IncomingStudent, trips_year=trips_year,
            trip_assignment=None,
            financial_aid=0, bus_assignment_round_trip=None,
            registration__doc_membership=YES
        )
        self.assertEqual(inc.compute_cost(), 50)

    def test_compute_cost_with_cancelled_trip(self):
        trips_year = self.init_trips_year()
        mommy.make(Settings, trips_year=trips_year, trips_cost=100)
        inc = mommy.make(
            IncomingStudent, trips_year=trips_year,
            trip_assignment=None,
            cancelled=True
        )
        # still charged if cancels last-minute
        self.assertEqual(inc.compute_cost(), 100)

    def test_netid_and_trips_year_are_unique(self):
        trips_year = self.init_trips_year()
        mommy.make(IncomingStudent, trips_year=trips_year, netid='w')
        with self.assertRaises(IntegrityError):
            mommy.make(IncomingStudent, trips_year=trips_year, netid='w')

    def test_bus_assignment_is_either_one_way_or_round_trip(self):
        msg = "Cannot have round-trip AND one-way bus assignments"
        with self.assertRaisesRegexp(ValidationError, msg):
            mommy.prepare(
                IncomingStudent,
                bus_assignment_round_trip=mommy.make(Stop),
                bus_assignment_to_hanover=mommy.make(Stop)
            ).full_clean()
        with self.assertRaisesRegexp(ValidationError, msg):
            mommy.prepare(
                IncomingStudent,
                bus_assignment_round_trip=mommy.make(Stop),
                bus_assignment_from_hanover=mommy.make(Stop)
            ).full_clean()

    def test_bus_cost_with_round_trip(self):
        inc = mommy.make(
            IncomingStudent,
            bus_assignment_round_trip=mommy.make(Stop, cost_round_trip=30, cost_one_way=15)
        )
        self.assertEqual(inc.bus_cost(), 30)

    def test_bus_cost_with_one_way(self):
        inc = mommy.make(
            IncomingStudent,
            bus_assignment_to_hanover=mommy.make(
                Stop, cost_round_trip=3, cost_one_way=100),
            bus_assignment_from_hanover=mommy.make(
                Stop, cost_round_trip=1, cost_one_way=200)
        )
        self.assertEqual(inc.bus_cost(), 300)

    def test_bus_cost_is_zero_if_no_bus(self):
        inc = mommy.make(
            IncomingStudent,
            bus_assignment_round_trip=None,
            bus_assignment_to_hanover=None,
            bus_assignment_from_hanover=None,
        )
        self.assertEqual(inc.bus_cost(), 0)

    def test_get_bus_stop_to_and_from_hanover_with_round_trip(self):
        stop = mommy.make(Stop)
        inc = mommy.make(
            IncomingStudent,
            bus_assignment_round_trip=stop
        )
        self.assertEqual(inc.get_bus_to_hanover(), stop)
        self.assertEqual(inc.get_bus_from_hanover(), stop)

    def test_get_bus_stop_to_hanover_one_way(self):
        stop = mommy.make(Stop)
        inc = mommy.make(
            IncomingStudent,
            bus_assignment_to_hanover=stop
        )
        self.assertEqual(inc.get_bus_to_hanover(), stop)

    def test_get_bus_stop_from_hanover_one_way(self):
        stop = mommy.make(Stop)
        inc = mommy.make(
            IncomingStudent,
            bus_assignment_from_hanover=stop
        )
        self.assertEqual(inc.get_bus_from_hanover(), stop)

    def test_lastname(self):
        inc = mommy.make(IncomingStudent, name='Rachek Zhao')
        self.assertEqual(inc.lastname, 'Zhao')

    def test_sort_by_lastname(self):
        inc1 = mommy.make(IncomingStudent, name='Rachel Zhao')
        inc2 = mommy.make(IncomingStudent, name='Lara P. Balick')
        inc3 = mommy.make(IncomingStudent, name='William A. P. Wolfe-McGuire')
        self.assertEqual([inc2, inc3, inc1], sort_by_lastname([inc1, inc2, inc3]))
        

class RegistrationModelTestCase(TripsYearTestCase):

    def test_must_agree_to_waiver(self):
        with self.assertRaisesMessage(
                ValidationError, "You must agree to the waiver"):
            mommy.make(Registration, waiver=NO).full_clean()

    def test_get_trip_assignment_returns_assignment(self):
        trips_year = self.init_current_trips_year()
        trip = mommy.make(Trip, trips_year=trips_year)
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
        trip1 = mommy.make(Trip, trips_year=trips_year, template__non_swimmers_allowed=False)
        trip2 = mommy.make(Trip, trips_year=trips_year, template__non_swimmers_allowed=True)
        reg = mommy.make(Registration, trips_year=trips_year, swimming_ability=Registration.NON_SWIMMER,
                         preferred_sections=[trip1.section, trip2.section])
        self.assertEqual(list(reg._base_trips_qs()), [trip2])

    def test_base_trips_qs_filters_for_preferred_and_available_sections(self):
        trips_year = self.init_current_trips_year()
        trip1 = mommy.make(Trip, trips_year=trips_year)
        trip2 = mommy.make(Trip, trips_year=trips_year)
        trip3 = mommy.make(Trip, trips_year=trips_year)
        reg = mommy.make(Registration, trips_year=trips_year, swimming_ability=Registration.COMPETENT,
                         preferred_sections=[trip1.section], available_sections=[trip2.section])
        self.assertEqual(set(reg._base_trips_qs()), set([trip1, trip2]))

    def test_get_firstchoice_trips(self):
        trips_year = self.init_current_trips_year()
        section1 = mommy.make('Section', trips_year=trips_year)
        section2 = mommy.make('Section', trips_year=trips_year)
        firstchoice_triptype = mommy.make('TripType', trips_year=trips_year)
        trip1 = mommy.make(Trip, trips_year=trips_year, section=section1, template__triptype=firstchoice_triptype)
        trip2 = mommy.make(Trip, trips_year=trips_year, section=section2, template__triptype=firstchoice_triptype)
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
        trip1 = mommy.make(Trip, trips_year=trips_year, section=section1, template__triptype=triptype)
        trip2 = mommy.make(Trip, trips_year=trips_year, section=section2, template__triptype=triptype)
        trip3 = mommy.make(Trip, trips_year=trips_year, section=section1)
        reg = mommy.make(Registration, trips_year=trips_year,
                         preferred_triptypes=[triptype],
                         swimming_ability=Registration.COMPETENT,
                         preferred_sections=[section1])
        self.assertEqual([trip1], list(reg.get_preferred_trips()))

    def test_get_preferred_trips_excludes_firstchoice_trips(self):
        trips_year = self.init_trips_year()
        firstchoice_trip = mommy.make(Trip, trips_year=trips_year)
        reg = mommy.make(Registration, trips_year=trips_year, 
                         firstchoice_triptype=firstchoice_trip.template.triptype,
                         preferred_triptypes=[firstchoice_trip.template.triptype],
                         preferred_sections=[firstchoice_trip.section],
                         swimming_ability=Registration.COMPETENT)
        self.assertEqual(list(reg.get_preferred_trips()), [])

    def test_get_available_trips(self):

        trips_year = self.init_current_trips_year()
        section1 = mommy.make('Section', trips_year=trips_year)
        section2 = mommy.make('Section', trips_year=trips_year)
        triptype = mommy.make('TripType', trips_year=trips_year)
        trip1 = mommy.make(Trip, trips_year=trips_year, section=section1, template__triptype=triptype)
        trip2 = mommy.make(Trip, trips_year=trips_year, section=section2, template__triptype=triptype)
        trip3 = mommy.make(Trip, trips_year=trips_year, section=section1)
        reg = mommy.make(Registration, trips_year=trips_year,
                         available_triptypes=[triptype],
                         swimming_ability=Registration.COMPETENT,
                         preferred_sections=[section1],
                         available_sections=[section1])
        self.assertEqual([trip1], list(reg.get_available_trips()))

    def test_get_available_trips_excludes_firstchoice_and_preffed_trips(self):
        trips_year = self.init_trips_year()
        firstchoice_trip = mommy.make(Trip, trips_year=trips_year)
        preffed_trip = mommy.make(Trip, trips_year=trips_year)
        reg = mommy.make(Registration, trips_year=trips_year, 
                         firstchoice_triptype=firstchoice_trip.template.triptype,
                         preferred_triptypes=[firstchoice_trip.template.triptype, preffed_trip.template.triptype],
                         available_triptypes=[preffed_trip.template.triptype],
                         preferred_sections=[firstchoice_trip.section, preffed_trip.section],
                         available_sections=[firstchoice_trip.section, preffed_trip.section],
                         swimming_ability=Registration.COMPETENT)
        self.assertEqual(list(reg.get_available_trips()), [])

    def test_get_incoming_student(self):
        trips_year = self.init_current_trips_year()
        reg = mommy.make(Registration, trips_year=trips_year)
        self.assertIsNone(reg.get_incoming_student())
        incoming = mommy.make(IncomingStudent, trips_year=trips_year, 
                              registration=reg)
        reg = Registration.objects.get(pk=reg.pk)
        self.assertEqual(reg.get_incoming_student(), incoming)

    def test_match(self):
        user = self.mock_incoming_student()
        trips_year = self.init_current_trips_year()
        incoming = mommy.make(IncomingStudent, netid=user.netid, trips_year=trips_year)
        reg = mommy.make(Registration, trips_year=trips_year, user=user)
        # clear automatic connections
        incoming.registration = None
        incoming.save()
        reg = Registration.objects.get(pk=reg.pk)
        reg.match()
        self.assertEqual(reg.trippee, incoming)

    def test_cannot_request_round_trip_and_one_way_bus(self):
        with self.assertRaisesRegex(ValidationError, "round-trip AND a one-way"):
            mommy.make(
                Registration,
                bus_stop_round_trip=mommy.make(Stop),
                bus_stop_to_hanover=mommy.make(Stop),
                waiver=YES
            ).full_clean()
        with self.assertRaisesRegex(ValidationError, "round-trip AND a one-way"):
            mommy.make(
                Registration,
                bus_stop_round_trip=mommy.make(Stop),
                bus_stop_from_hanover=mommy.make(Stop),
                waiver=YES
            ).full_clean()


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


class IncomingStudentsManagerTestCase(TripsYearTestCase):

    def test_unregistered(self):
        trips_year = self.init_current_trips_year()
        registration = mommy.make(Registration, trips_year=trips_year)
        registered = mommy.make(IncomingStudent, trips_year=trips_year, registration=registration)
        unregistered = mommy.make(IncomingStudent, trips_year=trips_year)
        self.assertEqual([unregistered], list(IncomingStudent.objects.unregistered(trips_year)))

    def test_availability_for_trip(self):
        trips_year = self.init_current_trips_year()
        trip = mommy.make(Trip, trips_year=trips_year)
        available = mommy.make(
            IncomingStudent, trips_year=trips_year, 
            registration__preferred_sections=[trip.section],
            registration__available_triptypes=[trip.template.triptype]
        )
        unavailable = mommy.make(
            IncomingStudent, trips_year=trips_year,
            registration__preferred_sections=[trip.section]
            # but no triptype pref
        )
        self.assertEqual(list(IncomingStudent.objects.available_for_trip(trip)), [available])

    def test_non_swimmer_availability_for_trip(self):
        trips_year = self.init_current_trips_year()
        trip = mommy.make(
            Trip, trips_year=trips_year, 
            template__non_swimmers_allowed=False
        )
        available = mommy.make(
            IncomingStudent, trips_year=trips_year, 
            registration__preferred_sections=[trip.section],
            registration__available_triptypes=[trip.template.triptype],
            registration__swimming_ability=Registration.BEGINNER
        )
        unavailable = mommy.make(
            IncomingStudent, trips_year=trips_year,
            registration__preferred_sections=[trip.section],
            registration__available_triptypes=[trip.template.triptype],
            registration__swimming_ability=Registration.NON_SWIMMER
        )
        self.assertEqual(list(IncomingStudent.objects.available_for_trip(trip)), [available])

    def test_passengers_to_hanover(self):
        trips_year = self.init_trips_year()
        rte = mommy.make(Route, trips_year=trips_year, category=Route.EXTERNAL)
        sxn = mommy.make(Section, trips_year=trips_year)
        psngr1 = mommy.make(
            IncomingStudent, trips_year=trips_year,
            bus_assignment_round_trip__route=rte,
            trip_assignment__section=sxn
        )
        psngr2 = mommy.make(
            IncomingStudent, trips_year=trips_year,
            bus_assignment_to_hanover__route=rte,
            trip_assignment__section=sxn
        )
        not_psngr = mommy.make(
            IncomingStudent, trips_year=trips_year, 
            bus_assignment_from_hanover__route=rte,
            trips_assignment__section=sxn
        )
        target = [psngr1, psngr2]
        actual = IncomingStudent.objects.passengers_to_hanover(
            trips_year, rte, sxn
        )
        self.assertQsEqual(actual, target)

    def test_passengers_from_hanover(self):
        trips_year = self.init_trips_year()
        rte = mommy.make(Route, trips_year=trips_year, category=Route.EXTERNAL)
        sxn = mommy.make(Section, trips_year=trips_year)
        psngr1 = mommy.make(
            IncomingStudent, trips_year=trips_year,
            bus_assignment_round_trip__route=rte,
            trip_assignment__section=sxn
        )
        psngr2 = mommy.make(
            IncomingStudent, trips_year=trips_year,
            bus_assignment_from_hanover__route=rte,
            trip_assignment__section=sxn
        )
        not_psngr = mommy.make(
            IncomingStudent, trips_year=trips_year, 
            bus_assignment_to_hanover__route=rte,
            trips_assignment__section=sxn
        )
        target = [psngr1, psngr2]
        actual = IncomingStudent.objects.passengers_from_hanover(
            trips_year, rte, sxn
        )
        self.assertQsEqual(actual, target)

    def test_with_trip(self):
        trips_year = self.init_trips_year()
        trip = mommy.make(
            Trip,
            trips_year=trips_year
        )
        assigned = mommy.make(
            IncomingStudent,
            trips_year=trips_year,
            trip_assignment=trip
        )
        not_assigned = mommy.make(
            IncomingStudent,
            trips_year=trips_year,
            trip_assignment=None
        )
        actual = list(IncomingStudent.objects.with_trip(trips_year))
        self.assertEqual(actual, [assigned])


class RegistrationViewsTestCase(WebTestCase):

    csrf_checks = False

    def test_registration_with_anonymous_user(self):
        self.init_current_trips_year()
        self.app.get(reverse('incoming:register'))

    def test_registration_connects_to_incoming(self):
        trips_year = self.init_current_trips_year()
        t = Timetable.objects.timetable()
        t.trippee_registrations_open += timedelta(-1)
        t.trippee_registrations_close += timedelta(1)
        t.save()
        mommy.make(Settings, trips_year=trips_year)
        user = self.mock_incoming_student()
        student = mommy.make(IncomingStudent, trips_year=trips_year, netid=user.netid)
        reg_data = {
            'name': 'test',
            'gender': 'hi',
            'previous_school': 'nah',
            'phone': '134',
            'email': 'asf@gmail.com',
            'tshirt_size': 'L',
            'regular_exercise': 'NO',
            'swimming_ability': 'BEGINNER',
            'camping_experience': 'NO',
            'hiking_experience': 'YES',
            'financial_assistance': 'YES',
            'waiver': 'YES',
            'doc_membership': 'NO',
            'green_fund_donation': 0,
        }
        url = reverse('incoming:register')
        self.app.post(url, reg_data, user=user)
        registration = Registration.objects.get()
        student = IncomingStudent.objects.get()
        self.assertEqual(registration.trippee, student)

    def test_non_student_registration(self):
        trips_year = self.init_trips_year()
        mommy.make(Settings, trips_year=trips_year)
        url = reverse('db:nonstudent_registration', kwargs={'trips_year': trips_year})
        data = {
            'name': 'test',
            'gender': 'm',
            'previous_school': 'nah',
            'phone': '134',
            'email': 'asf@gmail.com',
            'tshirt_size': 'L',
            'regular_exercise': 'NO',
            'swimming_ability': 'BEGINNER',
            'camping_experience': 'NO',
            'hiking_experience': 'YES',
            'financial_assistance': 'YES',
            'waiver': 'YES',
            'doc_membership': 'NO',
            'green_fund_donation': 0,
        }
        resp = self.app.post(url, data, user=self.mock_director()).follow()
        registration = Registration.objects.get()
        trippee = registration.trippee
        self.assertEqual(resp.request.path, trippee.detail_url())
        self.assertEqual(registration.user, DartmouthUser.objects.sentinel())
        self.assertEqual(trippee.name, 'test')
        self.assertEqual(trippee.netid, '')
        self.assertEqual(trippee.email, 'asf@gmail.com')
        self.assertEqual(trippee.blitz, 'asf@gmail.com')
        self.assertEqual(trippee.phone, '134')
        self.assertEqual(trippee.gender, 'm')


class RegistrationFormTestCase(TripsYearTestCase):

    def test_registration_form_without_instance_uses_current_trips_year(self):
        trips_year = self.init_current_trips_year()
        tt = mommy.make(TripType, trips_year=trips_year)
        mommy.make(Settings, trips_year=trips_year)  # must exist
        reg = mommy.make(Registration, trips_year=trips_year)
        form = RegistrationForm()
        self.assertEqual(list(form.fields['firstchoice_triptype'].queryset.all()), [tt])
    
    def test_registration_form_uses_trips_year_from_instance(self):
        trips_year = self.init_trips_year()
        prev_trips_year = self.init_previous_trips_year()
        tt = mommy.make(TripType, trips_year=prev_trips_year)
        mommy.make(Settings, trips_year=prev_trips_year)  # must exist
        reg = mommy.make(Registration, trips_year=prev_trips_year)
        form = RegistrationForm(instance=reg)
        self.assertEqual(list(form.fields['firstchoice_triptype'].queryset.all()), [tt])


class IncomingStudentViewsTestCase(WebTestCase):
    
    def test_delete_view(self):
        trips_year = self.init_current_trips_year()
        incoming = mommy.make(IncomingStudent, trips_year=trips_year)
        url = incoming.delete_url()
        res = self.app.get(url, user=self.mock_director())
        res = res.form.submit().follow()
        self.assertEqual(res.request.path, 
                         reverse('db:incomingstudent_index', kwargs={'trips_year': trips_year}))
        with self.assertRaises(IncomingStudent.DoesNotExist):
            IncomingStudent.objects.get(pk=incoming.pk)


class RegistrationManagerTestCase(TripsYearTestCase):
    
    def test_requesting_financial_aid(self):
        trips_year = self.init_current_trips_year()
        requesting = mommy.make(
            Registration, trips_year=trips_year,
            financial_assistance='YES'
        )
        not_requesting = mommy.make(
            Registration, trips_year=trips_year,
            financial_assistance='NO'
        )
        self.assertEqual(
            [requesting], list(Registration.objects.want_financial_aid(trips_year))
        )

    def test_requesting_bus(self):
        trips_year = self.init_current_trips_year()
        stop = mommy.make(
            Stop, trips_year=trips_year, route__category=Route.EXTERNAL
        )
        r1 = mommy.make(
            Registration, trips_year=trips_year, bus_stop_round_trip=stop
        )
        r2 = mommy.make(
            Registration, trips_year=trips_year, bus_stop_to_hanover=stop
        )
        r3 = mommy.make(
            Registration, trips_year=trips_year, bus_stop_from_hanover=stop
        )
        not_requesting = mommy.make(Registration, trips_year=trips_year)
        self.assertQsEqual(Registration.objects.want_bus(trips_year), [r1, r2, r3])

    def test_unmatched(self):
        trips_year = self.init_current_trips_year()
        matched = mommy.make(Registration, trips_year=trips_year)
        mommy.make(IncomingStudent, trips_year=trips_year, registration=matched)
        unmatched = mommy.make(Registration, trips_year=trips_year)
        self.assertEqual([unmatched], list(Registration.objects.unmatched(trips_year)))
        