class GrantMetadataSource(object):
    """Adds metadata to a grant:
    * metadata/source_license
    * metadata/source_license_name
    * metadata/sources_metadata
    """

    ADDITIONAL_DATA_KEY = "metadata"

    def update_additional_data(self, grant, source_file, additional_data, sources=None):

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

        # Aggregate licenses from all additional_data sources
        sources_metadata = {}
        if sources:
            for source_name, source_instance in sources.items():
                if hasattr(source_instance, "LICENCE") and hasattr(
                    source_instance, "ADDITIONAL_DATA_KEY"
                ):
                    sources_metadata[source_instance.ADDITIONAL_DATA_KEY] = {
                        "license": source_instance.LICENCE
                    }

        if sources_metadata:
            additional_data[self.ADDITIONAL_DATA_KEY][
                "sources_metadata"
            ] = sources_metadata
