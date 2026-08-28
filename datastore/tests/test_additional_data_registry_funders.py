import requests_mock
from django.test import TestCase
from django.test.utils import override_settings

from additional_data.models import RegistryFunder
from additional_data.sources.registry_funders import RegistryFundersSource
from db.models import Grant

REGISTRY_FUNDERS_URL = "http://localhost:8080/funders.json"

FUNDERS_RESPONSE = {
    "0013W000003j3aLQAQ": {
        "iD": "0013W000003j3aLQAQ",
        "orgIdentifier": "GB-example-b",
        "name": "ABC Trust",
        "sectors": "Philanthropy",
    },
    "0013W000003j2VPQAY": {
        "id": "0013W000003j2VPQAY",
        "orgIdentifier": "GB-CHC-1162855",
        "name": "Another Trust",
        "sectors": "Philanthropy",
    },
}


@override_settings(REGISTRY_FUNDERS_URL=REGISTRY_FUNDERS_URL)
class TestAdditionalDataRegistryFunders(TestCase):
    fixtures = ["test_data.json"]

    def test_import_registry_funders(self):
        source = RegistryFundersSource()

        with requests_mock.Mocker() as m:
            m.get(REGISTRY_FUNDERS_URL, json=FUNDERS_RESPONSE)
            added = source.import_registry_funders()

        self.assertEqual(added, 2)

        funder = RegistryFunder.objects.get(salesforce_id="0013W000003j3aLQAQ")
        self.assertEqual(funder.org_id, "GB-example-b")
        self.assertEqual(funder.data["name"], "ABC Trust")

    def test_import_registry_funders_replaces_existing(self):
        source = RegistryFundersSource()

        with requests_mock.Mocker() as m:
            m.get(REGISTRY_FUNDERS_URL, json=FUNDERS_RESPONSE)
            source.import_registry_funders()

            m.get(
                REGISTRY_FUNDERS_URL,
                json={
                    "0013W000003j3aLQAQ": FUNDERS_RESPONSE["0013W000003j3aLQAQ"],
                },
            )
            added = source.import_registry_funders()

        self.assertEqual(added, 1)
        self.assertEqual(RegistryFunder.objects.count(), 1)

    def test_update_additional_data(self):
        source = RegistryFundersSource()

        with requests_mock.Mocker() as m:
            m.get(REGISTRY_FUNDERS_URL, json=FUNDERS_RESPONSE)
            source.import_registry_funders()

        grant = Grant.objects.first()
        self.assertEqual(grant.data["fundingOrganization"][0]["id"], "GB-example-b")

        additional_data = {}
        source.update_additional_data(
            grant.data, grant.source_file.data, additional_data
        )

        self.assertIn(RegistryFundersSource.ADDITIONAL_DATA_KEY, additional_data)
        self.assertEqual(
            additional_data[RegistryFundersSource.ADDITIONAL_DATA_KEY]["name"],
            "ABC Trust",
        )

    def test_update_additional_data_no_match(self):
        source = RegistryFundersSource()

        grant = Grant.objects.first()
        additional_data = {}
        source.update_additional_data(
            grant.data, grant.source_file.data, additional_data
        )

        self.assertNotIn(RegistryFundersSource.ADDITIONAL_DATA_KEY, additional_data)

    def test_update_additional_data_no_funding_organization(self):
        source = RegistryFundersSource()

        grant = Grant.objects.first()
        del grant.data["fundingOrganization"]
        additional_data = {}
        source.update_additional_data(
            grant.data, grant.source_file.data, additional_data
        )

        self.assertNotIn(RegistryFundersSource.ADDITIONAL_DATA_KEY, additional_data)
