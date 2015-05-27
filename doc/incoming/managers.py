
import csv

from django.db import models

from doc.db.models import TripsYear


def get_netids(incoming_students):
    """ Return a set of incoming_students' netids """
    return set(map(lambda x: x.netid, incoming_students))


class IncomingStudentManager(models.Manager):

    def create_from_csv_file(self, file, trips_year):
        """
        Import incoming students from a CSV file. 

        If a student already exists in the database for this year, 
        ignore. We compare entries via netid. 
        
        Param trips_year is a string
        Returns a tuple (created_students, existing_students).

        TODO: parse/input incoming_status. How should this work?
        """

        trips_year = TripsYear.objects.get(pk=trips_year)
 
        reader = csv.DictReader(file)
            
        def parse_to_object(row):
            """ Parse a CSV row and return an incoming student object """
            if not row['Id']:
                return None
            return self.model(
                trips_year=trips_year,
                netid=row['Id'],
                name=row['Formatted Fml Name'],
                class_year=row['Class Year'],
                gender=row['Gender'],
                birthday=row['Birthday'],
                ethnic_code=row['Fine Ethnic Code'],
                email=row['EMail'],
                blitz=row['Blitz'],
                phone=row['PR Phone'],
                address="{}\n{}\n{}, {} {}\n{}".format(
                    row['PR Street 1'],
                    row['PR Street 2'],
                    row['PR City'], row['PR State'], row['PR Zip'],
                    row['Pr Nation Name']
                )
            )

        incoming = list(filter(None, map(parse_to_object, reader)))
        incoming_netids = get_netids(incoming)

        existing = self.model.objects.filter(trips_year=trips_year)
        existing_netids = get_netids(existing)

        netids_to_create = incoming_netids - existing_netids
        to_create = filter(lambda x: x.netid in netids_to_create, incoming)
        for obj in to_create:
            obj.save()

        ignored_netids = existing_netids & incoming_netids
        return (list(netids_to_create), list(ignored_netids))
        
       
