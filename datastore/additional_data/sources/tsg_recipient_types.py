class TSGRecipientTypesSource(object):
    """This adds a custom ThreeSixtyGiving recipient type of recipient to the additional data
    For now this is just organisation/individual
    """

    ADDITIONAL_DATA_KEY = "TSGRecipientType"

    def update_additional_data(self, grant, additional_data):
        try:
            grant["recipientOrganization"][0]["id"]
            additional_data[self.ADDITIONAL_DATA_KEY] = "Organisation"
        except (KeyError):
            additional_data[self.ADDITIONAL_DATA_KEY] = "Individual"
