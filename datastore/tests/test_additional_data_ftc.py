from django.test import TestCase

from additional_data.models import OrgInfoCache
from additional_data.sources.find_that_charity import FindThatCharitySource
from db.models import Grant


class TestAdditionalData(TestCase):
    fixtures = ["test_data.json"]

    ftc_file_data = [
        {"id": "ABC-119843", "income": 3000},
        {"id": "ABC-119841", "income": 2000, "orgIDs": '["one-234", "two-345"]'},
    ]

    ftc_file_data_2 = [
        {"id": "ABC-119843", "income": 3300},
        {"id": "ABC-119841", "income": 2200, "orgIDs": '["three-678", "one-234"]'},
    ]

    def test_find_that_charity_import(self):
        find_that_charity_source = FindThatCharitySource()

        # Test import w/ empty cache
        added = find_that_charity_source.process_csv(self.ftc_file_data, "ccni")

        self.assertEqual(added, 2, "unexpected number of org info objects added")

        org_info = OrgInfoCache.objects.get(org_id="ABC-119841")
        self.assertEqual(org_info.data["income"], 2000)
        self.assertEqual(len(org_info.org_ids), 2, "org-ids weren't parsed as an array")

        # Test updating existing entries
        added = find_that_charity_source.process_csv(
            self.ftc_file_data_2, "ccni", replace=True
        )

        org_info = OrgInfoCache.objects.get(org_id="ABC-119841")
        self.assertEqual(added, 2, "unexpected number of org info objects added")
        self.assertEqual(org_info.data["income"], 2200)
        self.assertSetEqual(set(org_info.org_ids), {"one-234", "three-678"})

    def test_find_that_charity_update_additional_data(self):
        find_that_charity_source = FindThatCharitySource()
        find_that_charity_source.process_csv(self.ftc_file_data, "ccew")

        grant = Grant.objects.first()
        # Setup this grant to have an org-id of our sample Org info cache data
        grant.data["recipientOrganization"][0]["id"] = self.ftc_file_data[0]["id"]

        additional_data = {}

        find_that_charity_source.update_additional_data(
            grant.data, grant.source_file.data, additional_data
        )

        self.assertEqual(
            FindThatCharitySource.ADDITIONAL_DATA_KEY in additional_data,
            True,
            "Additional data should have been added",
        )
