import csv
import json

import requests

from additional_data.models import OrgInfoCache


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

    def update_additional_data(self, grant, additional_data):
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

    def process_csv(self, file_data, org_type):
        """Returns total added. file_data array from csv"""
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

            if "orgIDs" not in row:
                row["orgIDs"] = None

            bulk_list.append(
                OrgInfoCache(
                    data=row, org_type=org_type, org_id=row["id"], org_ids=row["orgIDs"]
                )
            )
            added += 1

        OrgInfoCache.objects.bulk_create(bulk_list)

        return added

    def import_from_path(self, path, org_type=None):
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
            with requests.get(path, stream=True) as r:
                file_data = csv.DictReader(
                    r.iter_lines(decode_unicode=True), delimiter=","
                )
                added = self.process_csv(file_data, org_type)
        else:
            with open(path) as csv_file:
                file_data = csv.DictReader(csv_file, delimiter=",")
                added = self.process_csv(file_data, org_type)

        return added

    class OrgTypeNotKnownError(Exception):
        pass


def non_primary_org_ids_map():
    """Returns a dict of all non-primary org-ids and their corresponding primary org-id"""
    org_ids = {}
    orgs = OrgInfoCache.objects.filter(org_ids__len__gt=1).values_list(
        "org_ids", flat=True
    )
    # [[orgid, orgid], [orgid, orgid] ...]
    for org in orgs:
        # [ primary-org-id, secondary-org-id, ...org-id ]
        for non_primary_org_id in org[1:]:
            org_ids[non_primary_org_id] = org[0]
            # { non_primary_org_id : primary_org_id }

    return org_ids
