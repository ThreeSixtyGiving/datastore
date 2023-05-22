from additional_data.sources.find_that_charity import FindThatCharitySource
from additional_data.sources.geo_lookup import GeoLookupSource
from additional_data.sources.nspl import NSPLSource
from additional_data.sources.tsg_org_types import TSGOrgTypesSource
from additional_data.sources.additional_data_recipient_location import (
    AdditionalDataRecipientLocation,
)
from additional_data.sources.codelist_code import CodeListSource
from additional_data.sources.tsg_recipient_types import TSGRecipientTypesSource


class AdditionalDataGenerator(object):
    """Adds additional data to grant data"""

    def __init__(self):
        self.find_that_charity_source = FindThatCharitySource()
        self.nspl_source = NSPLSource()
        self.geo_lookup = GeoLookupSource()
        self.tsg_org_types = TSGOrgTypesSource()
        self.additional_data_recipient_location = AdditionalDataRecipientLocation()
        self.code_lists = CodeListSource()
        self.tsg_recipient_type = TSGRecipientTypesSource()
        # Initialise Other Sources here

    def create(self, grant):
        """Takes a grant's data and returns a dict of additional data"""

        additional_data = {}

        # This ordering is important for any data dependencies
        # Add other additional_data updaters here
        self.find_that_charity_source.update_additional_data(grant, additional_data)
        self.nspl_source.update_additional_data(grant, additional_data)
        self.geo_lookup.update_additional_data(grant, additional_data)
        self.tsg_org_types.update_additional_data(grant, additional_data)
        self.additional_data_recipient_location.update_additional_data(
            grant, additional_data
        )
        self.code_lists.update_additional_data(grant, additional_data)
        self.tsg_recipient_type.update_additional_data(grant, additional_data)

        return additional_data
