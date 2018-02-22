import logging
from json import JSONDecodeError

import requests


logger = logging.getLogger(__name__)

# URL constants. These endpoints have changed in the past,
# so check the source of https://lookup.dartmouth.edu/ if
# the lookup is broken.
#
# The following are valid query parameters:
# q=Lucia
# includeAlum=true
# field=uid
# field=displayName
# field=eduPersonPrimaryAffiliation
# field=mail&field=eduPersonNickname
# field=dcDeptclass
# field=dcAffiliation
# field=telephoneNumber
# field=dcHinmanaddr
DARTDM_URL = 'https://api-lookup.dartmouth.edu/v1/lookup'
DNDPROFILES_URL = 'http://dndprofiles.dartmouth.edu/profile'

# Key constants
NETID = 'netid'
NAME_WITH_YEAR = 'name_with_year'
NAME_WITH_AFFIL = 'name_with_affil'


class DartDmLookupException(Exception):
    pass


def dartdm_lookup(query_string):
    """
    Search in the Dartmouth Directory Manager for a user.

    Return a list of user records.
    """
    # Single character query is not allowed
    if len(query_string) < 2:
        return []

    params = {'q': query_string}
    r = requests.get(DARTDM_URL, params=params)

    return [{
        NETID: data['uid'],
        NAME_WITH_YEAR: data['displayName'],
        NAME_WITH_AFFIL: data['displayName'],
    } for data in r.json()['users']]


class EmailLookupException(Exception):
    pass


def lookup_email(netid):
    """
    Lookup the email address of a user, given their NetId.
    """
    params = {'lookup': netid, 'fields': ['email', 'netid']}
    r = requests.get(DNDPROFILES_URL, params=params)

    try:
        r_json = r.json()
    except JSONDecodeError:
        msg = 'Email lookup failed: invalid JSON'
        logger.info(msg)
        raise EmailLookupException(msg)

    # Not found
    if not r_json:
        msg = 'Email lookup failed: NetId %s not found' % netid
        logger.info(msg)
        raise EmailLookupException(msg)

    assert r_json['netid'] == netid

    return r_json['email']
