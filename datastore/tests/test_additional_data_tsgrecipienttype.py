from django.test import TestCase
from additional_data.sources.tsg_recipient_types import TSGRecipientTypesSource


class TestTSGRecipientTypes(TestCase):
    def test_recipient_is_individual(self):
        source = TSGRecipientTypesSource()

        grant = {
            "recipientIndividual": {
                "id": "1345-individual",
                "name": "Individual Recipient",
            },
        }

        additional_data_in = {}

        additional_data_out = {"TSGRecipientType": "Individual"}

        source.update_additional_data(grant, additional_data_in)

        self.assertEqual(
            additional_data_in,
            additional_data_out,
            "The expected additional data isn't correct",
        )

    def test_recipient_is_organisation(self):

        source = TSGRecipientTypesSource()

        grant = {
            "recipientOrganization": [
                {"id": "GB-COH-123553", "name": "Organisation that needs a grant"}
            ],
        }

        additional_data_in = {}

        additional_data_out = {"TSGRecipientType": "Organisation"}

        source.update_additional_data(grant, additional_data_in)

        self.assertEqual(
            additional_data_in,
            additional_data_out,
            "The expected additional data isn't correct",
        )
