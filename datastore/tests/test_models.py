from django.test import TransactionTestCase, TestCase

import db.models as db

import unittest.mock


class GetterRunTest(TransactionTestCase):
    fixtures = ["test_data.json"]

    def test_in_use(self):
        total_count = db.GetterRun.objects.all().count()
        in_use_count = db.GetterRun.objects.in_use().count()
        not_in_use_count = db.GetterRun.objects.not_in_use().count()

        self.assertLessEqual(in_use_count, total_count)
        self.assertLess(
            not_in_use_count, total_count
        )  # there should always be *some* in-use data
        self.assertEqual(in_use_count + not_in_use_count, total_count)


class GrantTest(TestCase):
    def test_convenience_fields_from_data(self):
        data = {
            "id": "360G-example-12345",
            "title": "Grant to 360 Giving",
            "currency": "GBP",
            "awardDate": "2019-01-31T00:00:00+00:00",
            "dataSource": "https://example.example/",
            "description": "example",
            "dateModified": "2019-07-18T00:00:00+00:00",
            "plannedDates": [
                {
                    "endDate": "2022-03-01T00:00:00+00:00",
                    "duration": 36,
                    "startDate": "2019-03-01T00:00:00+00:00",
                }
            ],
            "amountAwarded": 90000,
            "amountDisbursed": 30000,
            "classifications": [{"title": "Community - support for voluntary sector"}],
            "beneficiaryLocation": [
                {"name": "National/multi-regional", "countryCode": "GB"}
            ],
            "fundingOrganization": [
                {
                    "id": "GB-CHC-12345",
                    "name": "The Trust",
                    "department": "Trustee Committee",
                }
            ],
            "recipientOrganization": [
                {
                    "id": "GB-CHC-1164883",
                    "url": "http://www.threesixtygiving.co.uk",
                    "name": "360 Giving",
                    "postalCode": "SE11 5RR",
                    "charityNumber": "1164883",
                    "addressLocality": "London",
                },
                {"name": "Bad Example"},
                {"id": "GB-COH-09668396"},
            ],
        }

        # Mock relations to create a test Grant
        grant_gr = db.GetterRun()
        grant_sf = db.SourceFile(
            data={
                "publisher": dict(
                    org_id="XI-EXAMPLE-EXAMPLE",
                    name="example",
                    prefix="example",
                )
            },
            getter_run=grant_gr,
            quality={},
            aggregate={},
        )

        grant = db.Grant.from_data(
            data=data,
            getter_run=grant_gr,
            source_file=grant_sf,
            additional_data={},
        )

        # Check convenience fields
        self.assertSetEqual(
            set(grant.recipient_org_ids), {"GB-CHC-1164883", "GB-COH-09668396"}
        )

        self.assertSetEqual(set(grant.funding_org_ids), {"GB-CHC-12345"})

        self.assertEqual(grant.publisher_org_id, "XI-EXAMPLE-EXAMPLE")


def mock_non_primary_org_ids_lookup_maps():
    return {"GB-SECONDARY-12345": "GB-PRIMARY-12345"}, {}


@unittest.mock.patch(
    "db.models.non_primary_org_ids_lookup_maps", mock_non_primary_org_ids_lookup_maps
)
class RecipientUpdateAggregateTest(TestCase):
    def test_single_grant(self):
        recipient = db.Recipient()
        recipient.update_aggregate(
            {
                "currency": "GBP",
                "amountAwarded": 100,
                "awardDate": "2019-10-03T00:00:00+00:00",
                "fundingOrganization": [{"id": "GB-CHC-12345"}],
                "recipientOrganization": [
                    {"id": "GB-COH-12345"},
                ],
            }
        )
        self.assertEqual(recipient.aggregate["funders"], 1)
        self.assertEqual(recipient.aggregate["currencies"]["GBP"]["funders"], 1)

    def test_two_grants_from_same_funder(self):
        recipient = db.Recipient()
        recipient.update_aggregate(
            {
                "currency": "GBP",
                "amountAwarded": 100,
                "awardDate": "2019-10-03T00:00:00+00:00",
                "fundingOrganization": [{"id": "GB-CHC-12345"}],
                "recipientOrganization": [
                    {"id": "GB-COH-12345"},
                ],
            }
        )
        recipient.update_aggregate(
            {
                "currency": "GBP",
                "amountAwarded": 10000,
                "awardDate": "2020-10-03T00:00:00+00:00",
                "fundingOrganization": [{"id": "GB-CHC-12345"}],
                "recipientOrganization": [
                    {"id": "GB-COH-12345"},
                ],
            }
        )
        self.assertEqual(recipient.aggregate["funders"], 1)
        self.assertEqual(recipient.aggregate["currencies"]["GBP"]["funders"], 1)

    def test_two_grants_from_different_funders(self):
        recipient = db.Recipient()
        recipient.update_aggregate(
            {
                "currency": "GBP",
                "amountAwarded": 100,
                "awardDate": "2019-10-03T00:00:00+00:00",
                "fundingOrganization": [{"id": "GB-CHC-12345"}],
                "recipientOrganization": [
                    {"id": "GB-COH-12345"},
                ],
            }
        )
        recipient.update_aggregate(
            {
                "currency": "GBP",
                "amountAwarded": 10000,
                "awardDate": "2020-10-03T00:00:00+00:00",
                "fundingOrganization": [{"id": "GB-CHC-67890"}],
                "recipientOrganization": [
                    {"id": "GB-COH-12345"},
                ],
            }
        )
        self.assertEqual(recipient.aggregate["funders"], 2)
        self.assertEqual(recipient.aggregate["currencies"]["GBP"]["funders"], 2)

    def test_two_grants_from_different_funders_in_different_currencies(self):
        recipient = db.Recipient()
        recipient.update_aggregate(
            {
                "currency": "GBP",
                "amountAwarded": 100,
                "awardDate": "2019-10-03T00:00:00+00:00",
                "fundingOrganization": [{"id": "GB-CHC-12345"}],
                "recipientOrganization": [
                    {"id": "GB-COH-12345"},
                ],
            }
        )
        recipient.update_aggregate(
            {
                "currency": "EUR",
                "amountAwarded": 10000,
                "awardDate": "2020-10-03T00:00:00+00:00",
                "fundingOrganization": [{"id": "GB-CHC-67890"}],
                "recipientOrganization": [
                    {"id": "GB-COH-12345"},
                ],
            }
        )
        self.assertEqual(recipient.aggregate["funders"], 2)
        self.assertEqual(recipient.aggregate["currencies"]["GBP"]["funders"], 1)
        self.assertEqual(recipient.aggregate["currencies"]["EUR"]["funders"], 1)

    def test_two_grants_from_same_funder_but_different_funder_ids_used(self):
        recipient = db.Recipient()
        recipient.update_aggregate(
            {
                "currency": "GBP",
                "amountAwarded": 100,
                "awardDate": "2019-10-03T00:00:00+00:00",
                "fundingOrganization": [{"id": "GB-PRIMARY-12345"}],
                "recipientOrganization": [
                    {"id": "GB-COH-12345"},
                ],
            }
        )
        recipient.update_aggregate(
            {
                "currency": "GBP",
                "amountAwarded": 10000,
                "awardDate": "2020-10-03T00:00:00+00:00",
                "fundingOrganization": [{"id": "GB-SECONDARY-12345"}],
                "recipientOrganization": [
                    {"id": "GB-COH-12345"},
                ],
            }
        )
        self.assertEqual(recipient.aggregate["funders"], 1)
        self.assertEqual(recipient.aggregate["currencies"]["GBP"]["funders"], 1)
