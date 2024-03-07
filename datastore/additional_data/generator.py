from additional_data.sources.find_that_charity import FindThatCharitySource
from additional_data.sources.geo_lookup import GeoLookupSource
from additional_data.sources.nspl import NSPLSource
from additional_data.sources.tsg_org_types import TSGOrgTypesSource
from additional_data.sources.additional_data_recipient_location import (
    AdditionalDataRecipientLocation,
)
from additional_data.sources.codelist_code import CodeListSource
from additional_data.sources.tsg_recipient_types import TSGRecipientTypesSource


# This ordering is important for any data dependencies
# Add other additional_data updaters here
DATA_SOURCES = [
    "find_that_charity_source",
    "nspl_source",
    "geo_lookup",
    "tsg_org_types",
    "additional_data_recipient_location",
    "code_lists",
    "tsg_recipient_type",
]


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

    def create(self, grant, data_sources=DATA_SOURCES):
        """Takes a grant's data and returns a dict of additional data"""

        additional_data = {}

        for source in data_sources:
            try:
                getattr(self, source).update_additional_data(grant, additional_data)
            except AttributeError:
                raise Exception(f"Data source {source} is not a known data source.")

        return additional_data
