from django.test import TestCase
from additional_data.sources.codelist_code import CodeListSource


class TestCodeLists(TestCase):
    def test_code_list(self):
        self.maxDiff = None

        source = CodeListSource()
        source.import_codelists()

        grant = {
            "recipientOrganization": [{"location": [{"countryCode": "GB"}]}],
            "fundingOrganization": [{"location": [{"countryCode": "FR"}]}],
            "beneficiaryLocation": [{"countryCode": "AU"}],
            "toIndividualsDetails": {
                "primaryGrantReason": "GTIR040",
                "grantPurpose": ["GTIP170"],
            },
            "regrantType": "FRG010",
            "locationScope": "GLS040",
        }

        source_file = {}

        additional_data_in = {}

        expected_additional_data_out = {
            "codeListLookup": {
                "toIndividualsDetails": {
                    "primaryGrantReason": "Mental Health",
                    "secondaryGrantReason": "",
                    "grantPurpose": ["Exceptional costs"],
                },
                "regrantType": "Common Regrant",
                "locationScope": "Subnational region",
                "beneficiaryLocation_countryCode": "Australia",
                "fundingOrg_location_countryCode": "France",
                "recipientOrg_location_countryCode": "United Kingdom of Great Britain and Northern Ireland",
            }
        }

        source.update_additional_data(grant, source_file, additional_data_in)

        self.assertEqual(
            additional_data_in,
            expected_additional_data_out,
            "The expected additional data isn't correct",
        )
