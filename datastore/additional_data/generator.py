from additional_data.sources.find_that_charity import FindThatCharitySource
from additional_data.sources.geo_lookup import GeoLookupSource
from additional_data.sources.nspl import NSPLSource
from additional_data.sources.tsg_org_types import TSGOrgTypesSource
from additional_data.sources.additional_data_recipient_location import (
    AdditionalDataRecipientLocation,
)
from additional_data.sources.codelist_code import CodeListSource
from additional_data.sources.tsg_recipient_types import TSGRecipientTypesSource
from additional_data.sources.imd_snapshot import IMDSnapshotSource
from additional_data.sources.grant_metadata import GrantMetadataSource

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
    "imd_snapshot",
    "grant_metadata",
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
        self.imd_snapshot = IMDSnapshotSource()
        self.grant_metadata = GrantMetadataSource()
        # Initialise other additional data sources here

    def create(self, grant, source_file, additional_data_sources=DATA_SOURCES):
        """Takes a grant's data and returns a dict of additional data"""

        additional_data = {}

        for additional_data_source in additional_data_sources:
            try:
                source_instance = getattr(self, additional_data_source)
                if additional_data_source == "grant_metadata":
                    # Build sources dict excluding grant_metadata itself
                    sources_dict = {
                        key: getattr(self, key)
                        for key in additional_data_sources
                        if key != "grant_metadata"
                    }
                    source_instance.update_additional_data(
                        grant, source_file, additional_data, sources=sources_dict
                    )
                else:
                    source_instance.update_additional_data(
                        grant, source_file, additional_data
                    )
            except AttributeError:
                raise Exception(
                    f"Data source {additional_data_source} is not a known additional data source."
                )

        return additional_data
