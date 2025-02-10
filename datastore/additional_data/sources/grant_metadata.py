class GrantMetadataSource(object):
    """Adds metadata to a grant:
    * metadata/source_license
    * metadata/source_license_name
    """

    ADDITIONAL_DATA_KEY = "metadata"

    def update_additional_data(self, grant, source_file, additional_data):

        additional_data[self.ADDITIONAL_DATA_KEY] = {}

        # Add license information from the source of the data.
        if source_file.get("license_name"):
            additional_data[self.ADDITIONAL_DATA_KEY][
                "source_license_name"
            ] = source_file.get("license_name")

        if source_file.get("license"):
            additional_data[self.ADDITIONAL_DATA_KEY][
                "source_license"
            ] = source_file.get("license")
