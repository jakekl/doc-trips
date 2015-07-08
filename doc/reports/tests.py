import io
import csv
import tempfile
import unittest

from django.core.urlresolvers import reverse
from model_mommy import mommy

from doc.test.fixtures import WebTestCase, TripsTestCase
from doc.applications.tests import ApplicationTestMixin
from doc.applications.models import GeneralApplication
from doc.incoming.models import Registration, IncomingStudent
from doc.trips.models import ScheduledTrip
from doc.core.models import Settings
from doc.utils.choices import YES, NO, S, M, L, XL
from doc.reports.views import tshirt_counts


def save_and_open_csv(resp):
    """ 
    Save the file content return by response and
    open a CSV reader object over the saved file.
    """
    f = tempfile.NamedTemporaryFile()
    f.write(resp.content)
    f = open(f.name)  # open in non-binary mode
    return csv.DictReader(f)
    

class ReportViewsTestCase(WebTestCase, ApplicationTestMixin):

    def assertStopsIteration(self, iter):
        with self.assertRaises(StopIteration):
            next(iter)

    def test_volunteer_csv(self):
        trips_year = self.init_current_trips_year()
        application = self.make_application(trips_year=trips_year)
        non_applicant = self.make_application(trips_year=trips_year)
        non_applicant.croo_supplement.document = ''
        non_applicant.croo_supplement.save()
        non_applicant.leader_supplement.document = ''
        non_applicant.leader_supplement.save()
        res = self.app.get(reverse('db:reports:all_apps',
                                   kwargs={'trips_year': trips_year}),
                           user=self.mock_director())
        self.assertTrue(res['Content-Disposition'].startswith('attachment; filename="'))
        rows = list(save_and_open_csv(res))
        row = rows[0]
        self.assertEqual(row['name'], application.applicant.name)
        self.assertEqual(row['netid'], application.applicant.netid)
        self.assertEqual(len(rows), 1)
    
    def test_charges_report(self):
        trips_year = self.init_trips_year()
        mommy.make(Settings, doc_membership_cost=91)
        # incoming student to be charged:
        incoming1 = mommy.make(
            IncomingStudent,
            trips_year=trips_year,
            trip_assignment__trips_year=trips_year,  # force trip to exist
            bus_assignment__cost=37,
            financial_aid=15,
            registration__doc_membership=YES,
            registration__green_fund_donation=20
        )
        # another, without a registration
        incoming2 = mommy.make(
            IncomingStudent,
            trips_year=trips_year,
            trip_assignment__trips_year=trips_year,  # ditto
            financial_aid=0
        )
        # not charged because no trip assignment:
        mommy.make(IncomingStudent, trips_year=trips_year)

        url = reverse('db:reports:charges', kwargs={'trips_year': trips_year})
        resp = self.app.get(url, user=self.mock_director())

        rows = list(save_and_open_csv(resp))
        target = [{
            'name': incoming1.name,
            'netid': incoming1.netid,
            'total charge': str(incoming1.compute_cost()),
            'aid award (percentage)': '15',
            'bus': '37',
            'doc membership': '91',
            'green fund donation': '20',
        }, {
            'name': incoming2.name,
            'netid': incoming2.netid,
            'total charge': str(incoming2.compute_cost()),
            'aid award (percentage)': '',
            'bus': '',
            'doc membership': '',
            'green fund donation': '',
        }]
        self.assertEqual(rows, target)


class TShirtCountTestCase(TripsTestCase):
    
    def test_tshirt_count_leaders(self):
        trips_year = self.init_trips_year()
        mommy.make(
            GeneralApplication,
            trips_year=trips_year,
            status=GeneralApplication.LEADER,
            assigned_trip__trips_year=trips_year,
            tshirt_size=S
        )
        target = {
            S: 1, M: 0, L: 0, XL: 0
        }
        self.assertEqual(target, tshirt_counts(trips_year))
        
    def test_tshirt_count_croos(self):
        trips_year = self.init_trips_year()
        mommy.make(
            GeneralApplication,
            trips_year=trips_year,
            status=GeneralApplication.CROO,
            tshirt_size=M
        )
        target = {
            S: 0, M: 1, L: 0, XL: 0
        }
        self.assertEqual(target, tshirt_counts(trips_year))

    def test_tshirt_count_trippees(self):
        trips_year = self.init_trips_year()
        mommy.make(
            Registration,
            trips_year=trips_year,
            tshirt_size=L
        )
        target = {
            S: 0, M: 0, L: 1, XL: 0
        }
        self.assertEqual(target, tshirt_counts(trips_year))
        

        
