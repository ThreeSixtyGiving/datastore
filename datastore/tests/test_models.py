from django.test import TransactionTestCase, TestCase

import db.models as db


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
        grant_pub = db.Publisher(
            org_id="XI-EXAMPLE-EXAMPLE",
            name="example",
            aggregate={},
            additional_data={},
            data={},
            prefix="example",
            getter_run=grant_gr,
        )
        grant_sf = db.SourceFile(data={}, getter_run=grant_gr, quality={}, aggregate={})

        grant = db.Grant.from_data(
            data=data,
            getter_run=grant_gr,
            publisher=grant_pub,
            source_file=grant_sf,
            additional_data={},
        )

        # Check convenience fields
        self.assertSetEqual(
            set(grant.recipient_org_ids), {"GB-CHC-1164883", "GB-COH-09668396"}
        )

        self.assertSetEqual(set(grant.funding_org_ids), {"GB-CHC-12345"})

        self.assertEqual(grant.publisher_org_id, "XI-EXAMPLE-EXAMPLE")
