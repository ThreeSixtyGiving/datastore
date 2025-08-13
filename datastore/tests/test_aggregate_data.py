from django.test import TestCase
from django.forms.models import model_to_dict

from db.management.commands.manage_entities_data import update_entities
import db.models as db


class AggregateDataTest(TestCase):
    maxDiff = None
    fixtures = ["test_data.json"]

    def test_aggregate_data_doesnt_change(self):
        """Test that there haven't been other changes in the test data which
        require the aggregate data to be updated.
        """
        current_funders = list(
            db.Funder.objects.values_list("org_id", "non_primary_org_ids", "aggregate")
        )
        current_recipients = list(
            db.Recipient.objects.values_list(
                "org_id", "non_primary_org_ids", "aggregate"
            )
        )

        update_entities()

        post_update_funders = list(
            db.Funder.objects.all().values_list(
                "org_id", "non_primary_org_ids", "aggregate"
            )
        )
        post_update_recipients = list(
            db.Recipient.objects.all().values_list(
                "org_id", "non_primary_org_ids", "aggregate"
            )
        )

        self.assertEqual(
            current_funders,
            post_update_funders,
            "update_entities caused funder data to change in the test data, consider updating test_data?",
        )
        self.assertEqual(
            current_recipients,
            post_update_recipients,
            "update_entities caused recipient data to change in the test data, consider updating test data?",
        )

    def test_funder_aggregate_data(self):
        expected = {
            "additional_data": {"alternative_names": []},
            "aggregate": {
                "currencies": {
                    "GBP": {
                        "recipient_org": {
                            "avg": 500.94,
                            "grants": 50,
                            "max": 990,
                            "min": 46,
                            "total": 25047,
                        }
                    }
                },
                "grants": 50,
                "grants_ind": 0,
                "grants_org": 50,
                "maxAwardDate": "2019-10-03",
                "minAwardDate": "2019-10-03",
            },
            "name": "Funding for examples",
            "non_primary_org_ids": [],
            "org_id": "GB-example-b",
            "source": "GRANT",
        }

        found_data = model_to_dict(db.Funder.objects.get(org_id="GB-example-b"))
        # We don't care if the pk doesn't match
        del found_data["id"]

        self.assertEqual(found_data, expected)
        update_entities()
        self.assertEqual(found_data, expected)

    def test_recipient_aggregate_data(self):
        expected = {
            "additional_data": {"alternative_names": []},
            "aggregate": {
                "currencies": {
                    "GBP": {
                        "recipient_org": {
                            "avg": 504.0217391304348,
                            "grants": 46,
                            "max": 990,
                            "min": 46,
                            "total": 23185,
                        }
                    }
                },
                "grants": 46,
                "grants_ind": 0,
                "grants_org": 46,
                "maxAwardDate": "2019-10-03",
                "minAwardDate": "2019-10-03",
            },
            "name": "Receive an example grant",
            "non_primary_org_ids": ["360G-example-nonprimary"],
            "org_id": "360G-example-a",
            "source": "GRANT",
        }

        found_data = model_to_dict(db.Recipient.objects.get(org_id="360G-example-a"))
        # We don't care if the pk doesn't match
        del found_data["id"]

        self.assertEqual(found_data, expected)
        update_entities()
        self.assertEqual(found_data, expected)
