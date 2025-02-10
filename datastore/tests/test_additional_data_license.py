from django.test import TestCase

from additional_data.sources.grant_metadata import GrantMetadataSource
from db.models import Grant


class TestAdditionalDataLicense(TestCase):
    fixtures = ["test_data.json"]

    def test_publisher_license(self):
        grant_metadata_source = GrantMetadataSource()

        grant = Grant.objects.first()
        additional_data = {}

        expected_additional_data = {
            "metadata": {
                "source_license_name": "Creative Commons Attribution 4.0",
                "source_license": "https://creativecommons.org/licenses/by/4.0/",
            }
        }

        grant_metadata_source.update_additional_data(
            grant.data, grant.source_file.data, additional_data
        )

        self.assertEqual(
            GrantMetadataSource.ADDITIONAL_DATA_KEY in additional_data,
            True,
            "Additional license data was not added.",
        )

        self.assertEqual(
            additional_data,
            expected_additional_data,
            "The additional license data added is not correct.",
        )
