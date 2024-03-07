class AdditionalDataRecipientLocation(object):
    """Adds recipient* additional data to grant data

    These fields are used as the best available Region and District backward compatibility
    with grantnav and are sourced from locationLookup.

    https://github.com/ThreeSixtyGiving/grantnav/issues/867#issuecomment-1332505360

    Fields updated by this source.
       "recipientWardNameGeoCode",
       "recipientWardName",
       "recipientDistrictName",
       "recipientDistrictGeoCode",
       "recipientRegionName",
       "recipientCountryName",
       "recipientLocation", # string of all the above
    """

    def update_additional_data(self, grant, additional_data):
        # If we have locationLookup from beneficiaryLocation or we don't have any
        # recipientRegionName take whatever data we can from locationLookup instead
        # which is populated in geo_lookup
        try:
            additional_data["recipientRegionName"] = additional_data["locationLookup"][
                0
            ]["rgnnm"]
        except (IndexError, KeyError):
            pass

        try:
            additional_data["recipientDistrictName"] = additional_data[
                "locationLookup"
            ][0]["ladnm"]
            additional_data["recipientDistrictGeoCode"] = additional_data[
                "locationLookup"
            ][0]["ladcd"]
        except (IndexError, KeyError):
            pass

        # Oddity that GrantNav expects a country name as a region name if a region hasn't been found
        if not additional_data.get("recipientRegionName"):
            try:
                additional_data["recipientRegionName"] = additional_data[
                    "locationLookup"
                ][0]["ctrynm"]
            except (IndexError, KeyError):
                pass

        if not additional_data.get("recipientCountryName"):
            try:
                additional_data["recipientCountryName"] = additional_data[
                    "locationLookup"
                ][0]["ctrynm"]
            except (IndexError, KeyError):
                pass

        try:
            # We can only get ward for recipientOrganization not beneficiary due to the granularity of needing a postcode
            if "beneficiaryLocation" not in additional_data["locationLookup"][0].get(
                "source"
            ):
                additional_data["recipientWardName"] = additional_data[
                    "recipientOrganizationLocation"
                ]["ward_name"]
                additional_data["recipientWardNameGeoCode"] = additional_data[
                    "recipientOrganizationLocation"
                ]["ward"]
        except (IndexError, KeyError):
            pass

        # This is used for text searching in GrantNav
        additional_data["recipientLocation"] = " ".join(
            [
                additional_data.get("recipientDistrictName", ""),
                additional_data.get("recipientDistrictGeoCode", ""),
                additional_data.get("recipientWardName", ""),
                additional_data.get("recipientWardNameGeoCode", ""),
                additional_data.get("recipientRegionName", ""),
                additional_data.get("recipientCountryName", ""),
            ]
        )
