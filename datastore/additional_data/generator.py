from additional_data.sources.find_that_charity import FindThatCharitySource
from additional_data.sources.geo_lookup import GeoLookupSource
from additional_data.sources.local_files import LocalFilesSource
from additional_data.sources.nspl import NSPLSource


class AdditionalDataGenerator(object):
    """ Adds additional data to grant data """

    def __init__(self):
        self.local_files_source = LocalFilesSource()
        self.find_that_charity_source = FindThatCharitySource()
        self.nspl_source = NSPLSource()
        self.geo_lookup = GeoLookupSource()
        # Initialise Other Sources heres

    def create(self, grant):
        """ Takes a grant's data and returns a dict of additional data """

        additional_data = {}

        # This ordering is important for any data dependencies
        # Add other additional_data updaters here
        self.local_files_source.update_additional_data(grant, additional_data)
        self.find_that_charity_source.update_additional_data(grant, additional_data)
        self.nspl_source.update_additional_data(grant, additional_data)
        self.geo_lookup.update_additional_data(grant, additional_data)

        return additional_data
