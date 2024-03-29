import datetime

from django.urls import reverse_lazy
from django.test import TestCase
from django.core.management import call_command


current_year = datetime.date.today().year


class DashBoardAPITests(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "test_data.json")

    def test_dashboard_api_overview_grants(self):
        expected_data = {
            "aggregate": {
                "total": {
                    "grants": 50,
                    "GBP": 25047.0,
                    "publishers": 10,
                    "recipientOrganisations": 1,
                    "recipientIndividuals": 0,
                    "funders": 1,
                },
                "jsonFiles": 0,
                "csvFiles": 0,
                "xlsxFiles": 100,
                "odsFiles": 0,
                "awardYears": {
                    str(year): (50 if year == 2019 else 0)
                    for year in range(current_year, current_year - 10, -1)
                },
                "orgIdTypes": {},
                "awardedThisYear": 0,
                "awardedLastThreeMonths": 0,
            },
            "quality": {
                "hasBeneficiaryLocationName": 100,
                "hasRecipientOrgLocations": 100,
                "hasGrantDuration": 100,
                "hasGrantProgrammeTitle": 100,
                "hasGrantClassification": 0,
                "hasBeneficiaryLocationGeoCode": 100,
                "hasRecipientOrgCompanyOrCharityNumber": 0,
                "has50pcExternalOrgId": 0,
                "hasRecipientIndividualsCodelists": 100,
            },
        }

        data = self.client.get(reverse_lazy("api:overview") + "?mode=grants").json()

        self.assertEqual(data, expected_data)

    def test_dashboard_api_overview_publishers(self):
        expected_data = {
            "aggregate": {
                "total": {
                    "grants": 50,
                    "GBP": 25047.0,
                    "publishers": 10,
                    "recipientOrganisations": 1,
                    "recipientIndividuals": 0,
                    "funders": 1,
                },
                "jsonFiles": 0,
                "csvFiles": 0,
                "xlsxFiles": 100,
                "odsFiles": 0,
                "publishedThisYear": 0,
                "publishedLastThreeMonths": 0,
                "awardYears": {
                    str(year): (100 if year == 2019 else 0)
                    for year in range(current_year, current_year - 10, -1)
                },
                "recipientsExternalOrgId": {
                    "0% - 10%": 100.0,
                    "10% - 20%": 0.0,
                    "20% - 30%": 0.0,
                    "30% - 40%": 0.0,
                    "40% - 50%": 0.0,
                    "50% - 60%": 0.0,
                    "60% - 70%": 0.0,
                    "70% - 80%": 0.0,
                    "90% - 100%": 0.0,
                },
            },
            "quality": {
                "hasBeneficiaryLocationName": 100,
                "hasRecipientOrgLocations": 100,
                "hasGrantDuration": 100,
                "hasGrantProgrammeTitle": 100,
                "hasGrantClassification": 0,
                "hasBeneficiaryLocationGeoCode": 100,
                "hasRecipientOrgCompanyOrCharityNumber": 0,
                "has50pcExternalOrgId": 0,
                "hasRecipientIndividualsCodelists": 0,
            },
        }

        data = self.client.get(reverse_lazy("api:overview") + "?mode=publishers").json()

        self.assertEqual(data, expected_data)
