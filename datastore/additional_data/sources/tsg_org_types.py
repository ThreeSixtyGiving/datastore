import re

from additional_data.models import TSGOrgType


class TSGOrgTypesSource(object):
    """This adds a custom ThreeSixtyGiving organisation type of the funding organisation to the additional data"""

    ADDITIONAL_DATA_KEY = "TSGFundingOrgType"

    def __init__(self, *args, **kwargs):
        self.REGEX = 0
        self.VALUE = 1
        self.tsg_org_type_rules = []

        # Order - The highest priority rule gets added last as this is the one that will
        # be processed last and therefore overwrite any existing value.
        for tsg_org_type_rule in TSGOrgType.objects.all().order_by("priority"):
            try:
                self.tsg_org_type_rules.append(
                    (
                        re.compile(tsg_org_type_rule.regex),
                        tsg_org_type_rule.tsg_org_type,
                    )
                )
            # We have an invalid regex
            except re.error:
                continue

    def update_additional_data(self, grant, additional_data):
        try:
            funding_org_id = grant["fundingOrganization"][0]["id"]
        except (KeyError, TypeError) as e:
            print(e)
            return

        for org_type_rule in self.tsg_org_type_rules:
            if org_type_rule[self.REGEX].match(funding_org_id):
                additional_data[self.ADDITIONAL_DATA_KEY] = org_type_rule[self.VALUE]
