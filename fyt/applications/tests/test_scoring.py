import unittest

from django.urls import reverse
from model_mommy import mommy

from ..models import Score, Volunteer, Question
from . import ApplicationTestMixin

from fyt.applications.views.scoring import SHOW_SCORE_AVG_INTERVAL
from fyt.applications.forms import ScoreForm
from fyt.test import FytTestCase


class ScoreModelTestCase(ApplicationTestMixin, FytTestCase):

    def test_create_score_saves_croo_head_status(self):
        self.init_trips_year()
        app = self.make_application(trips_year=self.trips_year)

        score = Score.objects.create(
            trips_year=app.trips_year,
            application=app,
            grader=self.make_user(),  # Not a croo head
            leader_score=3,
            croo_score=4)
        self.assertFalse(score.croo_head)

        score = Score.objects.create(
            trips_year=app.trips_year,
            application=app,
            grader=self.make_croo_head(),  # Croo head
            leader_score=3,
            croo_score=4)
        self.assertTrue(score.croo_head)


class ScoreFormTestCase(ApplicationTestMixin, FytTestCase):

    def test_score_form(self):
        self.init_trips_year()
        application = self.make_application()
        ScoreForm(application=application)


class VolunteerManagerTestCase(ApplicationTestMixin, FytTestCase):

    def setUp(self):
        self.init_trips_year()
        self.make_user()
        self.make_director()
        self.make_directorate()
        self.make_croo_head()

    def make_scores(self, app, n):
        for i in range(n):
            mommy.make(Score, croo_head=False, trips_year=self.trips_year, application=app)

    def test_only_score_apps_for_this_year(self):
        last_year = self.init_old_trips_year()

        app1 = self.make_application(trips_year=self.trips_year)
        app2 = self.make_application(trips_year=last_year)

        self.assertEqual(app1, Volunteer.objects.next_to_score(self.user))

    def test_only_score_complete_apps(self):
        self.make_application(leader_willing=False, croo_willing=False)
        self.assertIsNone(Volunteer.objects.next_to_score(self.user))

    def test_user_only_scores_application_once(self):
        app = self.make_application()
        app.add_score(self.user, 4, 3)
        self.assertIsNone(Volunteer.objects.next_to_score(self.user))

    def test_only_score_pending_applications(self):
        app = self.make_application()  # PENDING
        for status, _ in Volunteer.STATUS_CHOICES:
            if status != Volunteer.PENDING:
                self.make_application(status=status)

        self.assertEqual(app, Volunteer.objects.next_to_score(self.user))

    def test_only_score_3_times(self):
        app = self.make_application()
        self.make_scores(app, Volunteer.NUM_SCORES)

        self.assertIsNone(Volunteer.objects.next_to_score(self.user))
        self.assertIsNone(Volunteer.objects.next_to_score(self.director))
        self.assertIsNone(Volunteer.objects.next_to_score(self.croo_head))

    def test_skip_application(self):
        app = self.make_application()
        app.skip(self.user)
        self.assertIsNone(Volunteer.objects.next_to_score(self.user))

    @unittest.expectedFailure
    def test_reserve_one_score_for_croo_heads(self):
        app = self.make_application()
        self.make_scores(app, Volunteer.NUM_SCORES - 1)

        self.assertIsNone(Volunteer.objects.next_to_score(self.user))
        self.assertEqual(app, Volunteer.objects.next_to_score(self.croo_head))

    def test_dont_reserve_croo_head_scores_for_leader_applications(self):
        app = self.make_application(croo_willing=False)
        self.make_scores(app, Volunteer.NUM_SCORES - 1)

        self.assertEqual(app, Volunteer.objects.next_to_score(self.user))
        self.assertEqual(app, Volunteer.objects.next_to_score(self.director))
        self.assertEqual(app, Volunteer.objects.next_to_score(self.directorate))
        self.assertEqual(app, Volunteer.objects.next_to_score(self.croo_head))

    def test_croo_heads_prefer_croo_apps(self):
        app1 = self.make_application(croo_willing=False)  # Leader only
        app2 = self.make_application()

        self.assertEqual(app2, Volunteer.objects.next_to_score(self.croo_head))

    def test_prefer_apps_with_fewer_scores(self):
        app1 = self.make_application()
        app2 = self.make_application()
        self.make_scores(app2, 1)
        self.assertEqual(app1, Volunteer.objects.next_to_score(self.director))

    def test_wtf_query(self):
        # Scored croo app
        app1 = self.make_application()
        self.make_scores(app1, 1)
        mommy.make(Score, application=app1, leader_score=3, croo_score=4,
                   croo_head=True)

        # Unscored leader app - should be prefered because it has fewer
        # scores and no more croo apps required croo head scores.
        app2 = self.make_application(croo_willing=False)

        self.assertEqual(app2, Volunteer.objects.next_to_score(self.croo_head))

    def test_score_progress(self):
        # 1/3 scores
        app1 = self.make_application()
        self.make_scores(app1, 1)

        # 10/3 scores becomes 3/3
        app2 = self.make_application()
        self.make_scores(app2, 10)

        # 0/3 scores
        app3 = self.make_application()

        progress = {
            'complete': 4,
            'total': 9,
            'percentage': 44
        }
        self.assertEqual(progress, Volunteer.objects.score_progress(self.trips_year))

    def test_score_progress_with_no_scores(self):
        # Don't divide by zero
        progress = {
            'complete': 0,
            'total': 0,
            'percentage': 100
        }
        self.assertEqual(progress, Volunteer.objects.score_progress(self.trips_year))


class ScoreViewsTestCase(ApplicationTestMixin, FytTestCase):

    def setUp(self):
        self.init_trips_year()
        self.make_director()
        self.make_grader()
        self.make_user()
        self.open_scoring()

    score_urls = [
        reverse('applications:score:next'),
        reverse('applications:score:no_applications_left'),
    ]

    not_available = 'applications/scoring_not_available.html'
    no_applications = 'applications/no_applications.html'

    def test_scoring_availability(self):
        self.close_scoring()
        for url in self.score_urls:
            resp = self.app.get(url, user=self.director).maybe_follow()
            self.assertTemplateUsed(resp, self.not_available)

        self.open_scoring()
        for url in self.score_urls:
            resp = self.app.get(url, user=self.director).maybe_follow()
            self.assertTemplateNotUsed(resp, self.not_available)

    def test_scoring_permissions(self):
        for url in self.score_urls + [reverse('applications:score:scoring')]:
            self.app.get(url, user=self.director)
            self.app.get(url, user=self.user, status=403)

    def test_score_application(self):
        app = self.make_application(trips_year=self.trips_year)
        question = mommy.make(Question, trips_year=self.trips_year, type=Question.ALL)
        app.answer_question(question, "An answer")

        url = reverse('applications:score:next')
        resp = self.app.get(url, user=self.grader).follow()
        resp.form['leader_score'] = 3
        resp.form['croo_score'] = 4
        resp.form['answer_1'] = 'A comment'
        resp.form['general'] = 'A comment about the whole'
        resp = resp.form.submit()

        self.assertEqual(len(app.scores.all()), 1)
        score = app.scores.first()
        self.assertEqual(score.leader_score, 3)
        self.assertEqual(score.croo_score, 4)
        self.assertEqual(score.grader, self.grader)
        self.assertEqual(score.application, app)
        self.assertEqual(score.trips_year, self.trips_year)
        self.assertEqual(len(score.answercomment_set.all()), 1)
        self.assertEqual(score.answercomment_set.first().comment, 'A comment')

    def test_skip_application(self):
        app = self.make_application(trips_year=self.trips_year)

        url = reverse('applications:score:next')
        resp = self.app.get(url, user=self.grader).follow()
        resp.form.submit(ScoreForm.SKIP)

        self.assertEqual(len(app.skips.all()), 1)
        skip = app.skips.first()
        self.assertEqual(skip.grader, self.grader)
        self.assertEqual(skip.application, app)
        self.assertEqual(skip.trips_year, self.trips_year)

        resp = self.app.get(url, user=self.grader).follow()
        self.assertTemplateUsed(resp, self.no_applications)

    def test_show_average_grade_in_messages(self):
        self.make_application(trips_year=self.trips_year)

        for i in range(SHOW_SCORE_AVG_INTERVAL):
            mommy.make(
                Score,
                trips_year=self.trips_year,
                grader=self.grader,
                leader_score=3,
                croo_score=4
            )

        url = reverse('applications:score:next')
        resp = self.app.get(url, user=self.grader).follow()

        messages = list(resp.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('average awarded leader score is 3.0', messages[0].message)
        self.assertIn('average awarded croo score is 4.0', messages[0].message)

    def test_delete_score_is_restricted_to_directors(self):
        score = mommy.make(Score, trips_year=self.trips_year)
        url = reverse('core:score:delete', kwargs={'trips_year': self.trips_year, 'pk': score.pk})
        res = self.app.get(url, user=self.make_tlt(), status=403)
        res = self.app.get(url, user=self.make_directorate(), status=403)
        res = self.app.get(url, user=self.grader, status=403)
        res = self.app.get(url, user=self.user, status=403)
        res = self.app.get(url, user=self.director)

    def test_delete_score_redirects_to_app(self):
        application = self.make_application(self.trips_year)
        score = mommy.make(Score, trips_year=self.trips_year, application=application)
        url = reverse('core:score:delete', kwargs={'trips_year': self.trips_year, 'pk': score.pk})
        resp = self.app.get(url, user=self.director)
        resp = resp.form.submit()
        self.assertRedirects(resp, application.detail_url())
