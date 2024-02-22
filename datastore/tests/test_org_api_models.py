from django.test import TransactionTestCase

from api.org.models import Organisation


class TestOrganisationModel(TransactionTestCase):
    fixtures = ["test_data.json"]

    def test_org_exists(self):
        self.assertTrue(Organisation.exists("360G-example-a"))

    def test_org_not_exists(self):
        self.assertFalse(Organisation.exists("XE-DOESNTEXIST"))
