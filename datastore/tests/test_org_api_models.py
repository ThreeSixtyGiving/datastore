from django.test import TransactionTestCase

from api.org.models import Organisation


class TestOrganisationModel(TransactionTestCase):
    fixtures = ["test_data.json"]

    funder_org_id = "GB-example-b"
    funder_org_name = "Funding for examples"

    recipient_org_id = "360G-example-a"
    recipient_org_name = "Receive an example grant"

    publisher_org_id = "GB-CHC-9000009"
    publisher_org_name = "The Heex1ieKu0 publisher"

    def test_org_exists(self):
        self.assertTrue(Organisation.exists(self.funder_org_id))
        self.assertTrue(Organisation.exists(self.recipient_org_id))
        self.assertTrue(Organisation.exists(self.publisher_org_id))

    def test_org_not_exists(self):
        self.assertFalse(Organisation.exists("XE-EXAMPLE-DOESNTEXIST"))

    def test_funder(self):
        org = Organisation.get(self.funder_org_id)
        self.assertEqual(org.org_id, self.funder_org_id)
        self.assertEqual(org.name, self.funder_org_name)
        self.assertIsNotNone(org.funder)
        self.assertIsNone(org.recipient)
        self.assertIsNone(org.publisher)

    def test_recipient(self):
        org = Organisation.get(self.recipient_org_id)
        self.assertEqual(org.org_id, self.recipient_org_id)
        self.assertEqual(org.name, self.recipient_org_name)
        self.assertIsNone(org.funder)
        self.assertIsNotNone(org.recipient)
        self.assertIsNone(org.publisher)

    def test_publisher(self):
        org = Organisation.get(self.publisher_org_id)
        self.assertEqual(org.org_id, self.publisher_org_id)
        self.assertEqual(org.name, self.publisher_org_name)
        self.assertIsNone(org.funder)
        self.assertIsNone(org.recipient)
        self.assertIsNotNone(org.publisher)

    def test_non_existent_org(self):
        with self.assertRaises(Organisation.DoesNotExist):
            _ = Organisation.get("XE-EXAMPLE-DOESNOTEXIST")
