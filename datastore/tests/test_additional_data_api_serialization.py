from django.test import TestCase

from db.models import Grant
from api.org.serializers import GrantSerializer


class TestGrantSerializerAdditionalData(TestCase):
    fixtures = ["test_data.json"]

    def test_additional_data_field_returns_raw_values(self):
        grant = Grant.objects.first()
        grant.additional_data = {
            "TSGRecipientType": "Organisation",
            "recipientOrgInfos": [{"id": "GB-CHC-1"}],
        }

        data = GrantSerializer(grant).data

        self.assertEqual(
            data["additional_data"],
            {
                "TSGRecipientType": "Organisation",
                "recipientOrgInfos": [{"id": "GB-CHC-1"}],
            },
        )

    def test_additional_data_field_excludes_metadata_key(self):
        grant = Grant.objects.first()
        grant.additional_data = {
            "TSGRecipientType": "Organisation",
            "metadata": {"source_license": "CC-BY"},
        }

        data = GrantSerializer(grant).data

        self.assertNotIn("metadata", data["additional_data"])
        self.assertEqual(data["additional_data_metadata"], {"source_license": "CC-BY"})

    def test_additional_data_field_absent_when_grant_has_none(self):
        grant = Grant.objects.first()
        grant.additional_data = None

        data = GrantSerializer(grant).data

        self.assertNotIn("additional_data", data)

    def test_additional_data_field_absent_when_only_metadata_present(self):
        grant = Grant.objects.first()
        grant.additional_data = {"metadata": {"source_license": "CC-BY"}}

        data = GrantSerializer(grant).data

        self.assertNotIn("additional_data", data)
