import json
import os

# Based on grantnav/import_to_elastic_search by David Raznick and Ben Webb
# https://github.com/ThreeSixtyGiving/grantnav/tree/master/dataload


class LocalFilesSource(object):
    """Adds additional data to grant data

    Fields added to additional_data by this source.
       "recipientOrganizationCanonical",
       "fundingOrganizationCanonical"
    """

    def __init__(self):
        self.id_name_org_mappings = {
            "fundingOrganization": {},
            "recipientOrganization": {},
        }

        self.data_files_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "data_files"
        )

        self._setup_charity_mappings()
        self._setup_org_name_mappings()

    def update_additional_data(self, grant, additional_data):
        self.update_additional_with_org_mappings(
            grant, "fundingOrganization", additional_data
        )
        self.update_additional_with_org_mappings(
            grant, "recipientOrganization", additional_data
        )

    def _setup_charity_mappings(self):
        """Setup info for charity names"""

        with open(os.path.join(self.data_files_dir, "charity_names.json")) as fd:

            charity_names = json.load(fd)
        self.id_name_org_mappings["recipientOrganization"].update(charity_names)

    def _setup_org_name_mappings(self):
        """Setup overrides for org name"""

        with open(
            os.path.join(self.data_files_dir, "primary_funding_org_name.json")
        ) as fd:
            funding_org_name = json.load(fd)
        self.id_name_org_mappings["fundingOrganization"].update(funding_org_name)

    def update_additional_with_org_mappings(self, grant, org_key, additional_data):
        mapping = self.id_name_org_mappings[org_key]
        orgs = grant.get(org_key, [])
        for org in orgs:
            org_id, name = org.get("id"), org.get("name")
            if not name:
                name = org_id
            if not org_id:
                return

            found_name = mapping.get(org_id)
            if not found_name:
                mapping[org_id] = name
                found_name = name

            additional_data["{}Canonical".format(org_key)] = {
                "id": org_id,
                "name": found_name,
            }
