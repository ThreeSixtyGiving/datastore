from additional_data.sources.find_that_charity import FindThatCharitySource
from additional_data.sources.local_files import LocalFilesSource


class AdditionalDataGenerator(object):
    """ Adds additional data to grant data """

    def __init__(self):
        self.local_files_source = LocalFilesSource()
        self.find_that_charity_source = FindThatCharitySource()
        # Initialise Other Sources heres

    def create(self, grant):
        """ Takes a grant's data and returns a dict of additional data """

        additional_data = {}

        # This ordering is important for any data dependencies
        # Add other additional_data updaters here
        self.local_files_source.update_additional_data(grant, additional_data)
        self.find_that_charity_source.update_additional_data(grant, additional_data)

        return additional_data
