import csv
import json
import logging
from typing import List, Tuple, Optional
from django.conf import settings

import requests

from additional_data.models import OrgInfoCache

logger = logging.getLogger(__name__)

# Tuple of (CSV URL, org type)
# See OrgInfoCache model for possible org types
FTC_SOURCES: List[Tuple[str, Optional[str]]] = [
    ("https://findthatcharity.uk/orgid/source/casc.csv", OrgInfoCache.CASC),
    ("https://findthatcharity.uk/orgid/source/ccew.csv", OrgInfoCache.CCEW),
    ("https://findthatcharity.uk/orgid/source/ccni.csv", OrgInfoCache.CCNI),
    ("https://findthatcharity.uk/orgid/source/oscr.csv", OrgInfoCache.OSCR),
    ("https://findthatcharity.uk/orgid/source/companies.csv", OrgInfoCache.COMPANIES),
    ("https://findthatcharity.uk/orgid/source/mutuals.csv", OrgInfoCache.MUTUALS),
    ("https://findthatcharity.uk/orgid/source/gor.csv", OrgInfoCache.GOR),
    ("https://findthatcharity.uk/orgid/source/ror.csv", OrgInfoCache.ROR),
    ("https://findthatcharity.uk/orgid/source/hesa.csv", OrgInfoCache.HESA),
    ("https://findthatcharity.uk/orgid/source/lae.csv", OrgInfoCache.LAE),
    ("https://findthatcharity.uk/orgid/source/lani.csv", OrgInfoCache.LANI),
    ("https://findthatcharity.uk/orgid/source/las.csv", OrgInfoCache.LAS),
    ("https://findthatcharity.uk/orgid/source/pla.csv", OrgInfoCache.PLA),
    ("https://findthatcharity.uk/orgid/source/coe.csv", OrgInfoCache.COE),
    (
        "https://findthatcharity.uk/orgid/source/officeforstudents.csv",
        OrgInfoCache.OFFICEFORSTUDENTS,
    ),
    (
        "https://findthatcharity.uk/orgid/source/nhsods-epraccur.csv",
        OrgInfoCache.NHSODS_EPRACCUR,
    ),
    ("https://findthatcharity.uk/orgid/source/nhsods-etr.csv", OrgInfoCache.NHSODS_ETR),
    (
        "https://findthatcharity.uk/orgid/source/nhsods-ensa.csv",
        OrgInfoCache.NHSODS_ENSA,
    ),
    (
        "https://findthatcharity.uk/orgid/source/nhsods-eccg.csv",
        OrgInfoCache.NHSODS_ECCG,
    ),
    (
        "https://findthatcharity.uk/orgid/source/nhsods-ecsu.csv",
        OrgInfoCache.NHSODS_ECSU,
    ),
    (
        "https://findthatcharity.uk/orgid/source/nhsods-espha.csv",
        OrgInfoCache.NHSODS_ESPHA,
    ),
    (
        "https://findthatcharity.uk/orgid/source/nhsods-wlhb.csv",
        OrgInfoCache.NHSODS_WLHB,
    ),
    ("https://findthatcharity.uk/orgid/source/nhsods-ect.csv", OrgInfoCache.NHSODS_ECT),
    ("https://findthatcharity.uk/orgid/source/rsl.csv", OrgInfoCache.RSL),
    ("https://findthatcharity.uk/orgid/source/gias.csv", OrgInfoCache.SCHOOLS_GIAS),
    (
        "https://findthatcharity.uk/orgid/source/nideptofeducation.csv",
        OrgInfoCache.SCHOOLS_NI,
    ),
    (
        "https://findthatcharity.uk/orgid/source/schoolsscotland.csv",
        OrgInfoCache.SCHOOLS_SCOTLAND,
    ),
    (
        "https://findthatcharity.uk/orgid/source/walesschools.csv",
        OrgInfoCache.SCHOOLS_WALES,
    ),
]


class FindThatCharitySource(object):
    """This is responsible for inputting and outputting data from the
    FindThatCharity (FTC) organisation info data sources"""

    ADDITIONAL_DATA_KEY = "recipientOrgInfos"

    def __init__(self, *args, **kwargs):
        # A basic internal memory cache to avoid hitting the db on duplicate
        # requests. Vastly speeds this process up.
        # OrgInfoCache db typical size is 565,110
        # This cache object typical size 68,458
        self._cache = {}

    def update_additional_data(self, grant, source_file, additional_data):
        # We can't do anything if this grant doesn't have a recipientOrganization
        if not grant.get("recipientOrganization"):
            return

        if "id" not in grant["recipientOrganization"][0]:
            return

        org_id = grant["recipientOrganization"][0]["id"]

        if "360G-" in org_id:
            # Not valid org-id
            return

        # Restart the cache after 300,000 this is approximately
        # 137.6MiB of memory.
        if len(self._cache.keys()) > 300000:
            self._cache = {}

        try:
            try:
                # Memory cache because a lot of these are going to be the same
                org_infos = self._cache[org_id]
                additional_data[self.ADDITIONAL_DATA_KEY] = org_infos
            except KeyError:
                org_infos = list(
                    OrgInfoCache.objects.filter(org_ids__contains=[org_id]).values_list(
                        "data", flat=True
                    )
                )

                additional_data[self.ADDITIONAL_DATA_KEY] = org_infos
                self._cache[org_id] = org_infos
        except OrgInfoCache.DoesNotExist:
            # Store no hit so that we don't bother the db for impossible queries
            self._cache[org_id] = None

    def process_csv(self, file_data, org_type, replace=False):
        """
        Returns total added. file_data array from csv.
        Set replace=True to update existing entries as well as creating new ones.
        """
        added = 0
        bulk_list = []

        for row in file_data:
            # Re-write string array "[ 'a','b','c' ]" values in the csv into arrays
            for key in row:
                if type(row[key]) == str and "[" in row[key]:
                    # Use json parser to turn the values into an array
                    # this could also be done by eval(val) but that is a little scary.
                    # The data also uses single quotes ['a'] to avoid csv breaking so
                    # those have to be replaced to be valid json.
                    try:
                        row[key] = json.loads(
                            '{ "a" : %s }' % row[key].replace("'", '"')
                        )["a"]
                    except json.decoder.JSONDecodeError:
                        # This can be incorrectly triggered via values with square brackets in
                        # e.g. A name [with brackets] Association
                        continue

            # Fall back to orgIDs if linked_orgs_verified not available, otherwise a minimal orgIDs array containing
            # just the primary orgID.
            if "orgIDs" not in row:
                row["orgIDs"] = [row["id"]]

            if "linked_orgs_verified" not in row:
                row["linked_orgs_verified"] = row["orgIDs"]

            bulk_list.append(
                OrgInfoCache(
                    data=row,
                    org_type=org_type,
                    org_id=row["id"],
                    org_ids=row["linked_orgs_verified"],
                )
            )
            added += 1

        if replace:
            OrgInfoCache.objects.bulk_create(
                bulk_list,
                update_conflicts=True,
                unique_fields=["org_id"],
                update_fields=["org_ids", "org_type", "fetched", "data"],
            )
        else:
            OrgInfoCache.objects.bulk_create(bulk_list)

        return added

    def import_from_path(self, path, org_type=None, replace=False):
        """Path can be http or file path, org_type if omitted we guess from the filename"""
        added = 0

        # Have a guess at the org type from the path
        if not org_type:
            for (short_type, long_type) in OrgInfoCache.ORG_TYPE:
                if short_type in path:
                    org_type = short_type
                    print("Guessed org_type %s" % org_type)
                    break

        if not org_type:
            raise self.OrgTypeNotKnownError

        if "http" in path:
            http_headers = {"User-Agent": "360Giving Datastore"}
            if settings.FTC_HEADER:
                ftc_header = settings.FTC_HEADER.split(":")
                http_headers[ftc_header[0].strip()] = ftc_header[1].strip()
            else:
                logger.warning(
                    "FTC_HEADER not set, note that FTC/OrgInfoCache data will be limited."
                )

            with requests.get(
                path,
                stream=True,
                headers=http_headers,
            ) as r:
                file_data = csv.DictReader(
                    r.iter_lines(decode_unicode=True), delimiter=","
                )
                added = self.process_csv(file_data, org_type, replace=replace)
        else:
            with open(path) as csv_file:
                file_data = csv.DictReader(csv_file, delimiter=",")
                added = self.process_csv(file_data, org_type, replace=replace)

        return added

    class OrgTypeNotKnownError(Exception):
        pass


def non_primary_org_ids_lookup_maps():
    """
    Returns a tuple of:
    * a dict of all non-primary org-ids mapped to their corresponding primary org-id.
    * a dict of all primary org-ids mapped to their corresponding non-primary org-ids.
    """
    non_primary_to_primary = {}
    primary_to_non_primary = {}

    # [[orgid, orgid], [orgid, orgid] ...]
    orgs = OrgInfoCache.objects.filter(org_ids__len__gt=1).values_list(
        "org_ids", flat=True
    )

    for org in orgs:
        # [ primary-org-id, secondary-org-id, ...org-id ]
        for non_primary_org_id in org[1:]:
            # { non_primary_org_id : primary_org_id }
            non_primary_to_primary[non_primary_org_id] = org[0]

        if len(org) > 1:
            # { primary_org_id : [non_primary_org_ids] }
            primary_to_non_primary[org[0]] = org[1:]

    return non_primary_to_primary, primary_to_non_primary
