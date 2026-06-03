from django.test import TestCase

from additional_data.sources.grant_metadata import GrantMetadataSource
from additional_data.sources.find_that_charity import FindThatCharitySource
from additional_data.sources.geo_lookup import GeoLookupSource
from additional_data.sources.nspl import NSPLSource
from additional_data.sources.codelist_code import CodeListSource
from db.models import Grant

OGL_V3 = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
CC_BY_4 = "https://creativecommons.org/licenses/by/4.0/"


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


class TestAdditionalDataSourceLicences(TestCase):
    fixtures = ["test_data.json"]

    def _assert_licence(self, source, expected_licence):
        grant = Grant.objects.first()
        additional_data = {}

        source.update_additional_data(
            grant.data, grant.source_file.data, additional_data
        )

        licence_key = f"{source.ADDITIONAL_DATA_KEY}_LICENCE"

        self.assertIn(
            licence_key,
            additional_data,
            f"{licence_key} was not added by {source.__class__.__name__}.",
        )
        self.assertEqual(
            additional_data[licence_key],
            expected_licence,
            f"{source.__class__.__name__} set the wrong licence value.",
        )

    def test_find_that_charity_licence(self):
        self._assert_licence(FindThatCharitySource(), OGL_V3)

    def test_geo_lookup_licence(self):
        self._assert_licence(GeoLookupSource(), OGL_V3)

    def test_nspl_licence(self):
        self._assert_licence(NSPLSource(), OGL_V3)

    def test_codelist_lookup_licence(self):
        self._assert_licence(CodeListSource(), CC_BY_4)
