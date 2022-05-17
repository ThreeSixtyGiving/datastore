from django.urls import reverse_lazy
from django.test import TestCase
from django.core.management import call_command


class DashBoardAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "test_data.json")

    def test_dashboard_api_overview_grants(self):
        expected_data = {
            "aggregate": {
                "total": {
                    "grants": 50,
                    "GBP": 26350.0,
                    "publishers": 10,
                    "recipients": 1,
                    "funders": 1,
                },
                "jsonFiles": 0,
                "csvFiles": 0,
                "xlsxFiles": 100,
                "odsFiles": 0,
                "awardYears": {
                    "2022": 0,
                    "2021": 0,
                    "2020": 0,
                    "2019": 50,
                    "2018": 0,
                    "2017": 0,
                    "2016": 0,
                    "2015": 0,
                    "2014": 0,
                    "2013": 0,
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
            },
        }

        data = self.client.get(reverse_lazy("api:overview") + "?mode=grants").json()

        self.assertEqual(data, expected_data)

    def test_dashboard_api_overview_publishers(self):
        expected_data = {
            "aggregate": {
                "total": {
                    "grants": 50,
                    "GBP": 26350.0,
                    "publishers": 10,
                    "recipients": 1,
                    "funders": 1,
                },
                "jsonFiles": 0,
                "csvFiles": 0,
                "xlsxFiles": 100,
                "odsFiles": 0,
                "publishedThisYear": 0,
                "publishedLastThreeMonths": 0,
                "awardYears": {
                    "2022": 0,
                    "2021": 0,
                    "2020": 0,
                    "2019": 100,
                    "2018": 0,
                    "2017": 0,
                    "2016": 0,
                    "2015": 0,
                    "2014": 0,
                    "2013": 0,
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
            },
        }

        data = self.client.get(reverse_lazy("api:overview") + "?mode=publishers").json()

        self.assertEqual(data, expected_data)
