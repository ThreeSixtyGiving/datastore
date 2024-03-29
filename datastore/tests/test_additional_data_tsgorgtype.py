from django.test import TestCase

from additional_data.models import TSGOrgType
from additional_data.sources.tsg_org_types import TSGOrgTypesSource
from db.models import Grant


class TestTSGOrgTypeAdditionalData(TestCase):
    fixtures = ["test_data.json", "default_tsg_org_types.json"]

    def test_update_additional_data_low_priority(self):
        tsg_org_types = TSGOrgTypesSource()
        grant = Grant.objects.last()

        grant.data["fundingOrganization"][0]["id"] = "ABC-1234"

        additional_data = {}

        tsg_org_types.update_additional_data(grant.data, additional_data)

        lowest_priority_org_type = (
            TSGOrgType.objects.order_by("priority").first().tsg_org_type
        )

        self.assertTrue(
            lowest_priority_org_type
            in additional_data[TSGOrgTypesSource.ADDITIONAL_DATA_KEY],
            "Expected %s" % lowest_priority_org_type,
        )

    def test_update_additional_data_multiple_rules(self):
        # National lottery but also GOR
        # Should prioritise national lottery over government
        tsg_org_types = TSGOrgTypesSource()
        grant = Grant.objects.last()
        grant.data["fundingOrganization"][0]["id"] = "GB-GOR-PC390"

        additional_data = {}
        tsg_org_types.update_additional_data(grant.data, additional_data)

        self.assertTrue(
            "Lottery Distributor"
            in additional_data[TSGOrgTypesSource.ADDITIONAL_DATA_KEY],
            "Expected 'Lottery Distributor'",
        )
