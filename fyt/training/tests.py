from datetime import date

from django.core.exceptions import ValidationError
from django.urls import reverse
from model_mommy import mommy

from fyt.applications.models import Volunteer
from fyt.applications.tests import ApplicationTestMixin
from fyt.test import FytTestCase
from fyt.training.forms import (
    AttendanceForm,
    CompletedSessionsForm,
    FirstAidCertificationFormset,
    SessionRegistrationForm,
    SignupForm,
)
from fyt.training.models import Attendee, FirstAidCertification, Session, Training


# Don't let model_mommy bung up the OneToOne creation
def make_attendee(trips_year=None, registered_sessions=None, **kwargs):
    volunteer = mommy.make(
        Volunteer, trips_year=trips_year, applicant__email='test@gmail.com'
    )
    for k, v in kwargs.items():
        setattr(volunteer.attendee, k, v)

    if registered_sessions:
        volunteer.attendee.registered_sessions.add(registered_sessions)

    volunteer.attendee.save()
    return volunteer.attendee


class SessionModelTestCase(FytTestCase):
    def setUp(self):
        self.init_trips_year()
        self.session = mommy.make(Session, trips_year=self.trips_year)
        self.attendee = make_attendee(
            trips_year=self.trips_year, registered_sessions=self.session
        )

    def test_attendee_emails(self):
        self.assertQsEqual(self.session.registered_emails(), ['test@gmail.com'])

    def test_full(self):
        self.assertFalse(self.session.full())
        for i in range(Session.DEFAULT_CAPACITY):
            make_attendee(trips_year=self.trips_year, registered_sessions=self.session)
        self.assertTrue(self.session.full())


class AttendeeModelTestCase(ApplicationTestMixin, FytTestCase):
    def setUp(self):
        self.init_trips_year()

    def test_attendee_is_created_for_each_volunteer(self):
        volunteer = mommy.make(Volunteer, trips_year=self.trips_year)
        attendee = volunteer.attendee
        self.assertEqual(attendee.trips_year, self.trips_year)

    def test_can_train(self):
        results = {
            Volunteer.CROO: True,
            Volunteer.LEADER: True,
            Volunteer.LEADER_WAITLIST: True,
            Volunteer.PENDING: False,
            Volunteer.PENDING: False,
            Volunteer.CANCELED: False,
            Volunteer.REJECTED: False,
        }
        trainable = []
        for status, allowed in results.items():
            a = self.make_application(status=status).attendee
            self.assertEqual(a.can_register, allowed)
            if allowed:
                trainable.append(a)

        self.assertQsEqual(Attendee.objects.trainable(self.trips_year), trainable)


class AttendeeTrainingTestCase(FytTestCase):
    def setUp(self):
        self.init_trips_year()
        self.training = mommy.make(Training, trips_year=self.trips_year)
        self.attendee1 = make_attendee(trips_year=self.trips_year)
        self.attendee2 = make_attendee(trips_year=self.trips_year)
        self.session = mommy.make(
            Session, trips_year=self.trips_year, training=self.training
        )
        self.session.completed.add(self.attendee2)

    def test_trainings_to_sessions(self):
        self.assertEqual(self.attendee1.trainings_to_sessions(), {self.training: None})
        self.assertEqual(
            self.attendee2.trainings_to_sessions(), {self.training: self.session}
        )

    def test_training_complete_on_model(self):
        self.assertFalse(self.attendee1.training_complete())
        self.assertTrue(self.attendee2.training_complete())

    def test_training_complete_manager(self):
        self.assertQsEqual(
            Attendee.objects.training_complete(self.trips_year), [self.attendee2]
        )

    def test_training_incomplete_manager(self):
        self.assertQsEqual(
            Attendee.objects.training_incomplete(self.trips_year), [self.attendee1]
        )


# TODO: move this to volunteer app?
class VolunteerFirstAidTestCase(ApplicationTestMixin, FytTestCase):
    def setUp(self):
        self.init_trips_year()

        # No certifications
        self.incomplete1 = self.make_application()

        # No CPR
        self.incomplete2 = self.make_application()
        mommy.make(
            FirstAidCertification, volunteer=self.incomplete2, name='WFA', verified=True
        )

        # No first aid
        self.incomplete3 = self.make_application()
        mommy.make(
            FirstAidCertification, volunteer=self.incomplete3, name='CPR', verified=True
        )

        # Both unverified
        self.incomplete4 = self.make_application()
        mommy.make(
            FirstAidCertification,
            volunteer=self.incomplete4,
            name='WFA',
            verified=False,
        )
        mommy.make(
            FirstAidCertification,
            volunteer=self.incomplete4,
            name='CPR',
            verified=False,
        )

        self.incompletes = [
            self.incomplete1,
            self.incomplete2,
            self.incomplete3,
            self.incomplete4,
        ]

        # All good
        self.complete = self.make_application()
        mommy.make(
            FirstAidCertification, volunteer=self.complete, name='EMT', verified=True
        )
        mommy.make(
            FirstAidCertification, volunteer=self.complete, name='CPR', verified=True
        )

    def test_first_aid_complete(self):
        self.assertQsEqual(Volunteer.objects.first_aid_complete(), [self.complete])

    def test_first_aid_incomplete(self):
        self.assertQsEqual(Volunteer.objects.first_aid_incomplete(), self.incompletes)

    def test_first_aid_compete_model_method(self):
        self.assertTrue(self.complete.first_aid_complete)
        for v in self.incompletes:
            self.assertFalse(v.first_aid_complete)


class FirstAidCertificationModelTestCase(FytTestCase):
    def setUp(self):
        self.init_trips_year()
        self.cert1 = mommy.make(
            FirstAidCertification,
            trips_year=self.trips_year,
            name='WFR',
            expiration_date=date(2019, 2, 25),
        )
        self.cert2 = mommy.make(
            FirstAidCertification,
            trips_year=self.trips_year,
            name=FirstAidCertification.OTHER,
            other='ABC',
            expiration_date=date(2020, 3, 23),
        )
        self.cert3 = mommy.make(
            FirstAidCertification, trips_year=self.trips_year, name='', other='ABC'
        )

    def test_get_name(self):
        self.assertEqual(self.cert1.get_name(), 'WFR')

    def test_get_name_other(self):
        self.assertEqual(self.cert2.get_name(), 'ABC')

    def test_get_name_without_explicit_other(self):
        self.assertEqual(self.cert3.get_name(), 'ABC')

    def test_str(self):
        self.assertEqual(str(self.cert1), 'WFR (exp. 02/25/19)')
        self.assertEqual(str(self.cert2), 'ABC (exp. 03/23/20)')

    def test_requires_name_or_other(self):
        with self.assertRaises(ValidationError):
            mommy.make(FirstAidCertification, name='', other='').full_clean()

    def test_other_name_must_have_other_field(self):
        with self.assertRaises(ValidationError):
            mommy.make(
                FirstAidCertification, name=FirstAidCertification.OTHER, other=''
            ).full_clean()


class SessionRegistrationFormTestCase(ApplicationTestMixin, FytTestCase):
    def setUp(self):
        self.init_trips_year()
        self.session = mommy.make(Session, trips_year=self.trips_year)
        self.attendee = self.make_application(status=Volunteer.LEADER).attendee
        self.make_application(status=Volunteer.REJECTED)

    def test_queryset_is_all_trainable_volunteers(self):
        form = SessionRegistrationForm(instance=self.session)
        self.assertQsEqual(form.fields['registered'].queryset, [self.attendee])

    def test_initial_is_populated(self):
        self.session.registered.add(self.attendee)
        form = SessionRegistrationForm(instance=self.session)
        self.assertQsEqual(form.fields['registered'].initial, [self.attendee])

    def test_form_saves_registration(self):
        form = SessionRegistrationForm(
            {'registered': [self.attendee]}, instance=self.session
        )
        form.save()
        self.session.refresh_from_db()
        self.assertQsEqual(self.session.registered.all(), [self.attendee])

    def test_form_removes_registrations(self):
        self.session.registered.add(self.attendee)
        form = SessionRegistrationForm({'registered': []}, instance=self.session)
        form.save()
        self.session.refresh_from_db()
        self.assertQsEqual(self.session.registered.all(), [])


class AttendenceFormTestCase(FytTestCase):
    def setUp(self):
        self.init_trips_year()
        self.session = mommy.make(Session, trips_year=self.trips_year)
        self.attendee = make_attendee(
            trips_year=self.trips_year, registered_sessions=self.session
        )
        self.not_attending = make_attendee(trips_year=self.trips_year)

    def test_queryset_is_all_registered_volunteers(self):
        form = AttendanceForm(instance=self.session)
        self.assertQsEqual(form.fields['completed'].queryset, [self.attendee])

    def test_initial_is_populated(self):
        self.session.completed.add(self.attendee)
        form = AttendanceForm(instance=self.session)
        self.assertQsEqual(form.fields['completed'].initial, [self.attendee])

    def test_form_saves_attendance(self):
        self.assertQsEqual(self.session.completed.all(), [])
        form = AttendanceForm({'completed': [self.attendee]}, instance=self.session)
        form.save()
        self.session.refresh_from_db()
        self.assertQsEqual(self.session.completed.all(), [self.attendee])

    def test_form_removes_attendance(self):
        self.session.completed.add(self.attendee)
        form = AttendanceForm({'completed': []}, instance=self.session)
        form.save()
        self.session.refresh_from_db()
        self.assertQsEqual(self.session.completed.all(), [])


class CompletedSessionsFormTestCase(FytTestCase):
    def setUp(self):
        self.init_trips_year()
        self.init_old_trips_year()

    def test_complete_sessions_queryset(self):
        session = mommy.make(Session, trips_year=self.trips_year)
        old_session = mommy.make(Session, trips_year=self.old_trips_year)
        attendee = make_attendee(trips_year=self.trips_year)
        form = CompletedSessionsForm(instance=attendee)
        self.assertQsEqual(form.fields['complete_sessions'].queryset, [session])


class SignupFormTestCase(FytTestCase):
    def setUp(self):
        self.init_trips_year()

    def test_session_size_is_capped(self):
        session = mommy.make(Session, trips_year=self.trips_year)
        for i in range(Session.DEFAULT_CAPACITY):
            make_attendee(trips_year=self.trips_year, registered_sessions=session)

        attendee = make_attendee(trips_year=self.trips_year)
        form = SignupForm({'registered_sessions': [session]}, instance=attendee)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'registered_sessions': [
                    "The following sessions are full: {}. Please choose another "
                    "session. If this is the only time you can attend, please "
                    "contact the Trip Leader Trainers directly.".format(session)
                ]
            },
        )

    def test_dont_check_capacity_when_previously_registered(self):
        session = mommy.make(Session, trips_year=self.trips_year)
        attendee = make_attendee(
            trips_year=self.trips_year, registered_sessions=session
        )

        # Then session fills up
        for i in range(Session.DEFAULT_CAPACITY):
            make_attendee(trips_year=self.trips_year, registered_sessions=session)

        form = SignupForm({'registered_sessions': [session]}, instance=attendee)
        self.assertTrue(form.is_valid())
        self.assertQsEqual(form.cleaned_data['registered_sessions'], [session])

    def test_registered_sessions_are_filtered_for_trips_year(self):
        self.init_old_trips_year()
        session = mommy.make(Session, trips_year=self.trips_year)
        old_session = mommy.make(Session, trips_year=self.old_trips_year)
        attendee = make_attendee(trips_year=self.trips_year)

        form = SignupForm(instance=attendee)
        self.assertQsEqual(form.fields['registered_sessions'].queryset, [session])


class FirstAidCertificationFormsetTestCase(ApplicationTestMixin, FytTestCase):
    def setUp(self):
        self.init_trips_year()
        self.application = self.make_application()

    def test_formset_save(self):
        formset = FirstAidCertificationFormset(
            prefix='formset',
            trips_year=self.trips_year,
            instance=self.application,
            data={
                'formset-INITIAL_FORMS': '0',
                'formset-TOTAL_FORMS': '3',
                'formset-MIN_NUM_FORMS': '',
                'formset-MAX_NUM_FORMS': '',
                'formset-0-name': 'FA',
                'formset-0-other': '',
                'formset-0-expiration_date': '2/24/2017',
            },
        )
        self.assertTrue(formset.is_valid())
        formset.save()
        self.application.refresh_from_db()
        self.assertQsContains(
            self.application.first_aid_certifications.all(),
            [{'name': 'FA', 'other': '', 'expiration_date': date(2017, 2, 24)}],
        )


class TrainingViewsTestCase(ApplicationTestMixin, FytTestCase):
    def setUp(self):
        self.init_trips_year()
        self.make_user()
        self.make_director()
        self.make_directorate()
        self.make_croo_head()
        self.make_tlt()
        self.make_safety_lead()

    def test_db_view_permissions(self):
        session = mommy.make(Session, trips_year=self.trips_year)
        update_urls = [
            session.update_url(),
            session.delete_url(),
            Session.create_url(self.trips_year),
            reverse('core:session:update_attendance', kwargs=session.obj_kwargs()),
        ]
        for url in update_urls:
            self.app.get(url, user=self.tlt)
            self.app.get(url, user=self.director)
            self.app.get(url, user=self.safety_lead)
            self.app.get(url, user=self.directorate)
            self.app.get(url, user=self.user, status=403)
            self.app.get(url, user=self.croo_head, status=403)

    def test_external_view_permissions(self):
        results = {
            Volunteer.CROO: 200,
            Volunteer.LEADER: 200,
            Volunteer.LEADER_WAITLIST: 200,
            Volunteer.PENDING: 403,
            Volunteer.PENDING: 403,
            Volunteer.CANCELED: 403,
            Volunteer.REJECTED: 403,
        }

        url = reverse('training:signup')
        for status, code in results.items():
            app = mommy.make(Volunteer, trips_year=self.trips_year, status=status)
            self.app.get(url, user=app.applicant, status=code)


class FirstAidViewsTestCase(ApplicationTestMixin, FytTestCase):
    def setUp(self):
        self.init_trips_year()
        self._timetable().save()
        self.make_director()
        self.make_application(status=Volunteer.LEADER)
        self.url = reverse(
            'core:attendee:first_aid', kwargs={'trips_year': self.trips_year}
        )

    def test_num_queries(self):
        with self.assertNumQueries(16):
            self.app.get(self.url, user=self.director)

    def test_first_aid_update_redirect(self):
        # Visit first aid list page
        resp1 = self.app.get(self.url, user=self.director)
        # Edit the volunteer's certifications
        resp2 = resp1.click(description="Edit")
        # Submit form
        resp3 = resp2.form.submit()
        # Redirects back to first aid list
        self.assertRedirects(resp3, self.url)
