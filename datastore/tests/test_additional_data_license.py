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

    def test_source_licenses_aggregation(self):
        """Test that GrantMetadataSource aggregates licenses from all sources"""
        grant = Grant.objects.first()
        additional_data = {}

        # Create source instances
        sources = {
            "find_that_charity_source": FindThatCharitySource(),
            "geo_lookup": GeoLookupSource(),
            "nspl_source": NSPLSource(),
            "code_lists": CodeListSource(),
        }

        grant_metadata_source = GrantMetadataSource()

        # Call with sources parameter
        grant_metadata_source.update_additional_data(
            grant.data, grant.source_file.data, additional_data, sources=sources
        )

        # Verify the structure
        self.assertIn(
            "metadata",
            additional_data,
            "metadata key was not added.",
        )

        self.assertIn(
            "sources_metadata",
            additional_data["metadata"],
            "sources_metadata was not aggregated by GrantMetadataSource.",
        )

        sources_metadata = additional_data["metadata"]["sources_metadata"]

        # Verify each source's license is present
        self.assertIn(
            "recipientOrgInfos",
            sources_metadata,
            "FindThatCharitySource license not aggregated.",
        )
        self.assertEqual(
            sources_metadata["recipientOrgInfos"]["license"],
            OGL_V3,
            "FindThatCharitySource has wrong license.",
        )

        self.assertIn(
            "locationLookup",
            sources_metadata,
            "GeoLookupSource license not aggregated.",
        )
        self.assertEqual(
            sources_metadata["locationLookup"]["license"],
            OGL_V3,
            "GeoLookupSource has wrong license.",
        )

        self.assertIn(
            "recipientOrganizationLocation",
            sources_metadata,
            "NSPLSource license not aggregated.",
        )
        self.assertEqual(
            sources_metadata["recipientOrganizationLocation"]["license"],
            OGL_V3,
            "NSPLSource has wrong license.",
        )

        self.assertIn(
            "codeListLookup",
            sources_metadata,
            "CodeListSource license not aggregated.",
        )
        self.assertEqual(
            sources_metadata["codeListLookup"]["license"],
            CC_BY_4,
            "CodeListSource has wrong license.",
        )
