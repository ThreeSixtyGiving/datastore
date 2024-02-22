import datetime

from django.urls import reverse_lazy
from django.test import TestCase
from django.core.management import call_command


current_year = datetime.date.today().year


class OrgAPITestCase(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "test_data.json")

    # Examples Orgs and Grants plucked from the test dataset
    funder_org_id = "GB-example-b"
    funder_org_name = "Funding for examples"
    funder_grant_id = "360G-kahM5Ooc2u"

    recipient_org_id = "360G-example-a"
    recipient_org_name = "Receive an example grant"
    recipient_grant_id = "360G-Eiz4Veij8o"

    publisher_org_id = "GB-CHC-9000009"
    publisher_org_name = "The Heex1ieKu0 publisher"

    org_list_entries = [
        # (org_id, name)
        (funder_org_id, funder_org_name),
        (recipient_org_id, recipient_org_name),
        (publisher_org_id, publisher_org_name),
    ]

    #
    # Funder
    #

    def test_funder_detail(self):
        test_reverse_kwargs = {"org_id": self.funder_org_id}

        expected_self_url = reverse_lazy(
            "api:organisation-detail", kwargs=test_reverse_kwargs
        )

        expected_grants_made_url = reverse_lazy(
            "api:organisation-grants-made", kwargs=test_reverse_kwargs
        )
        expected_received_made_url = reverse_lazy(
            "api:organisation-grants-received", kwargs=test_reverse_kwargs
        )

        expected_org_data = {
            "self": "http://testserver" + expected_self_url,
            "grants_made": "http://testserver" + expected_grants_made_url,
            "grants_received": "http://testserver" + expected_received_made_url,
            "funder": {
                "aggregate": {
                    "grants": 50,
                    "currencies": {
                        "GBP": {
                            "avg": 500.94,
                            "max": 990.0,
                            "min": 46.0,
                            "total": 25047.0,
                            "grants": 50,
                        }
                    },
                }
            },
            "recipient": None,
            "publisher": None,
            "org_id": self.funder_org_id,
            "name": self.funder_org_name,
        }

        data = self.client.get(
            f"/api/experimental/org/{self.funder_org_id}/",
            headers={"accept": "application/json"},
        ).json()

        self.assertEqual(data, expected_org_data)

    def test_funder_grants_received(self):
        """A Funder-only Org should have received no grants."""

        data = self.client.get(
            f"/api/experimental/org/{self.funder_org_id}/grants_received/",
            headers={"accept": "application/json"},
        ).json()

        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    def test_funder_grants_made(self):
        # Check that the expected grant exists in the set of grants
        expected_grant_data = {
            "data": {
                "id": self.funder_grant_id,
                "title": "The luumuch5Ir grant",
                "currency": "GBP",
                "awardDate": "2019-10-03T00:00:00+00:00",
                "description": "Example grant description",
                "dateModified": "2019-08-03T00:00:00Z",
                "fromOpenCall": "Yes",
                "plannedDates": [
                    {
                        "endDate": "2017-02-15",
                        "duration": 4,
                        "startDate": "2016-10-03",
                    }
                ],
                "amountAwarded": 971,
                "grantProgramme": [
                    {"code": "00200200220", "title": "Example grants August 2019"}
                ],
                "beneficiaryLocation": [
                    {
                        "name": "England; Scotland; Wales",
                        "geoCode": "K02000001",
                        "geoCodeType": "CTRY",
                    }
                ],
                "fundingOrganization": [
                    {"id": "GB-example-b", "name": "Funding for examples"}
                ],
                "recipientOrganization": [
                    {
                        "id": "360G-example-a",
                        "name": "Receive an example grant",
                        "postalCode": "SW1 1AA",
                        "streetAddress": "10 Downing street",
                        "addressCountry": "United Kingdom",
                        "addressLocality": "LONDON",
                    }
                ],
            },
            "publisher": {
                "self": "http://testserver"
                + reverse_lazy(
                    "api:organisation-detail", kwargs={"org_id": "GB-CHC-9000000"}
                ),
                "org_id": "GB-CHC-9000000",
            },
            "recipients": [
                {
                    "self": "http://testserver"
                    + reverse_lazy(
                        "api:organisation-detail", kwargs={"org_id": "360G-example-a"}
                    ),
                    "org_id": "360G-example-a",
                }
            ],
            "funders": [
                {
                    "self": "http://testserver"
                    + reverse_lazy(
                        "api:organisation-detail", kwargs={"org_id": "GB-example-b"}
                    ),
                    "org_id": "GB-example-b",
                }
            ],
            "grant_id": self.funder_grant_id,
        }

        data = self.client.get(
            f"/api/experimental/org/{self.funder_org_id}/grants_made/",
            headers={"accept": "application/json"},
        ).json()

        self.assertEqual(data["count"], 50)

        grants = {grant["grant_id"]: grant for grant in data["results"]}

        self.assertIn(self.funder_grant_id, grants)
        self.assertEqual(expected_grant_data, grants[self.funder_grant_id])

    #
    # Recipient
    #

    def test_recipient_org_detail(self):
        """Check Recipient API detail."""
        test_reverse_kwargs = {"org_id": self.recipient_org_id}

        expected_self_url = reverse_lazy(
            "api:organisation-detail", kwargs=test_reverse_kwargs
        )

        expected_grants_made_url = reverse_lazy(
            "api:organisation-grants-made", kwargs=test_reverse_kwargs
        )
        expected_received_made_url = reverse_lazy(
            "api:organisation-grants-received", kwargs=test_reverse_kwargs
        )

        expected_org_data = {
            "self": "http://testserver" + expected_self_url,
            "grants_made": "http://testserver" + expected_grants_made_url,
            "grants_received": "http://testserver" + expected_received_made_url,
            "funder": None,
            "recipient": {
                "aggregate": {
                    "grants": 50,
                    "currencies": {
                        "GBP": {
                            "avg": 500.94,
                            "max": 990.0,
                            "min": 46.0,
                            "total": 25047.0,
                            "grants": 50,
                        }
                    },
                }
            },
            "publisher": None,
            "org_id": self.recipient_org_id,
            "name": self.recipient_org_name,
        }

        data = self.client.get(
            f"/api/experimental/org/{self.recipient_org_id}/",
            headers={"accept": "application/json"},
        ).json()

        self.assertEqual(data, expected_org_data)

    def test_recipient_grants_received(self):
        """Assert that the Recipient gets the expected grant."""

        # Check that the expected grant exists in the set of grants
        expected_grant_data = {
            "data": {
                "id": self.recipient_grant_id,
                "title": "The IKoesou1ze grant",
                "currency": "GBP",
                "awardDate": "2019-10-03T00:00:00+00:00",
                "description": "Example grant description",
                "dateModified": "2019-08-03T00:00:00Z",
                "fromOpenCall": "Yes",
                "plannedDates": [
                    {"endDate": "2017-02-15", "duration": 4, "startDate": "2016-10-03"}
                ],
                "amountAwarded": 210,
                "grantProgramme": [
                    {"code": "00200200220", "title": "Example grants August 2019"}
                ],
                "beneficiaryLocation": [
                    {
                        "name": "England; Scotland; Wales",
                        "geoCode": "K02000001",
                        "geoCodeType": "CTRY",
                    }
                ],
                "fundingOrganization": [
                    {"id": "GB-example-b", "name": "Funding for examples"}
                ],
                "recipientOrganization": [
                    {
                        "id": "360G-example-a",
                        "name": "Receive an example grant",
                        "postalCode": "SW1 1AA",
                        "streetAddress": "10 Downing street",
                        "addressCountry": "United Kingdom",
                        "addressLocality": "LONDON",
                    }
                ],
            },
            "publisher": {
                "self": "http://testserver"
                + reverse_lazy(
                    "api:organisation-detail", kwargs={"org_id": "GB-CHC-9000007"}
                ),
                "org_id": "GB-CHC-9000007",
            },
            "recipients": [
                {
                    "self": "http://testserver"
                    + reverse_lazy(
                        "api:organisation-detail", kwargs={"org_id": "360G-example-a"}
                    ),
                    "org_id": "360G-example-a",
                }
            ],
            "funders": [
                {
                    "self": "http://testserver"
                    + reverse_lazy(
                        "api:organisation-detail", kwargs={"org_id": "GB-example-b"}
                    ),
                    "org_id": "GB-example-b",
                }
            ],
            "grant_id": self.recipient_grant_id,
        }

        data = self.client.get(
            f"/api/experimental/org/{self.recipient_org_id}/grants_received/",
            headers={"accept": "application/json"},
        ).json()

        self.assertEqual(data["count"], 50)

        grants = {grant["grant_id"]: grant for grant in data["results"]}

        self.assertIn(self.recipient_grant_id, grants)
        self.assertEqual(expected_grant_data, grants[self.recipient_grant_id])

    def test_recipient_grants_made(self):
        """A Recipient-only Org should not make any grants."""
        data = self.client.get(
            f"/api/experimental/org/{self.recipient_org_id}/grants_made/",
            headers={"accept": "application/json"},
        ).json()

        self.assertEqual(data["count"], 0)

    #
    # Publisher
    #

    def test_publisher_detail(self):

        expected_self_url = reverse_lazy(
            "api:organisation-detail", kwargs={"org_id": self.publisher_org_id}
        )

        expected_grants_made_url = reverse_lazy(
            "api:organisation-grants-made", kwargs={"org_id": self.publisher_org_id}
        )
        expected_grants_received_url = reverse_lazy(
            "api:organisation-grants-received", kwargs={"org_id": self.publisher_org_id}
        )

        expected_org_data = {
            "self": "http://testserver" + expected_self_url,
            "grants_made": "http://testserver" + expected_grants_made_url,
            "grants_received": "http://testserver" + expected_grants_received_url,
            "funder": None,
            "recipient": None,
            "publisher": {"prefix": "360g-Ap0inaap5e"},
            "org_id": self.publisher_org_id,
            "name": self.publisher_org_name,
        }

        data = self.client.get(
            f"/api/experimental/org/{self.publisher_org_id}/",
            headers={"accept": "application/json"},
        ).json()

        self.assertEqual(data, expected_org_data)

    def test_publisher_grants_made(self):
        """A Publisher-only Org should have made no grants."""
        data = self.client.get(
            f"/api/experimental/org/{self.publisher_org_id}/grants_received/",
            headers={"accept": "application/json"},
        ).json()

        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    def test_publisher_grants_received(self):
        """A Publisher-only Org should have received no grants."""

        data = self.client.get(
            f"/api/experimental/org/{self.publisher_org_id}/grants_received/",
            headers={"accept": "application/json"},
        ).json()

        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    #
    # Org List
    #

    def test_org_list(self):
        """Check that the given Org is in the Org List"""
        data = self.client.get(
            "/api/experimental/org/",
            headers={"accept": "application/json"},
        ).json()

        self.assertGreaterEqual(data["count"], 3)

        for org_id, org_name in self.org_list_entries:
            with self.subTest(org_id=org_id):
                expected_entry = {
                    "org_id": org_id,
                    "name": org_name,
                    "self": "http://testserver"
                    + reverse_lazy(
                        "api:organisation-detail", kwargs={"org_id": org_id}
                    ),
                }

                self.assertIn(expected_entry, data["results"])

    #
    # Non-existent Org
    #
    def test_non_existent_org_detail(self):
        """Check for 404 on non-existent Org detail"""
        response = self.client.get(
            reverse_lazy(
                "api:organisation-detail", kwargs={"org_id": "XE-EXAMPLE-DOESNTEXIST"}
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_non_existent_org_grants_made(self):
        """Check for 404 on non-existent Org grants made"""
        response = self.client.get(
            reverse_lazy(
                "api:organisation-grants-made",
                kwargs={"org_id": "XE-EXAMPLE-DOESNTEXIST"},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_non_existent_org_grants_received(self):
        """Check for 404 on non-existent Org grants received"""
        response = self.client.get(
            reverse_lazy(
                "api:organisation-grants-received",
                kwargs={"org_id": "XE-EXAMPLE-DOESNTEXIST"},
            )
        )

        self.assertEqual(response.status_code, 404)
