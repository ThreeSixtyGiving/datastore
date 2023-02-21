from django.test import TestCase
from additional_data.sources.codelist_code import CodeListSource


class TestCodeLists(TestCase):
    def test_code_list(self):
        source = CodeListSource()
        source.import_codelists()

        grant = {
            "toIndividualsDetails": {
                "primaryGrantReason": "GTIR040",
                "grantPurpose": ["GTIP170"],
            },
            "regrantType": "FRG010",
        }

        additional_data_in = {}

        additional_data_out = {
            "codeListLookup": {
                "toIndividualDetails": {
                    "primaryGrantReason": "Mental Health",
                    "secondaryGrantReason": "",
                    "grantPurpose": ["Exceptional costs"],
                },
                "regrantType": "Common Regrant",
            }
        }

        source.update_additional_data(grant, additional_data_in)

        self.assertEqual(
            additional_data_in,
            additional_data_out,
            "The expected additional data isn't correct",
        )
