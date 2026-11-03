from django.test import SimpleTestCase

from bulk_data.schema import field_title


class FieldTitleTest(SimpleTestCase):
    def test_leaf_title_with_no_nesting(self):
        properties = {"id": {"type": "string", "title": "Identifier"}}
        self.assertEqual(field_title(properties, {}, "id"), "Identifier")

    def test_nested_titles_are_joined_with_colon(self):
        properties = {
            "recipientOrganization": {
                "type": "array",
                "title": "Recipient Org",
                "items": {
                    "type": "object",
                    "properties": {"id": {"type": "string", "title": "Identifier"}},
                },
            }
        }
        self.assertEqual(
            field_title(properties, {}, "recipientOrganization.id"),
            "Recipient Org: Identifier",
        )

    def test_ref_to_a_container_drops_its_own_generic_title(self):
        definitions = {
            "Event": {
                "type": "object",
                "title": "Event",
                "properties": {"startDate": {"type": "string", "title": "Start Date"}},
            }
        }
        properties = {
            "plannedDates": {
                "type": "array",
                "title": "Planned Dates",
                "items": {"$ref": "#/definitions/Event"},
            }
        }
        self.assertEqual(
            field_title(properties, definitions, "plannedDates.startDate"),
            "Planned Dates: Start Date",
        )

    def test_ref_with_a_sibling_title_overrides_the_definitions_title(self):
        definitions = {
            "Person": {
                "type": "object",
                "properties": {"id": {"type": "string", "title": "Identifier"}},
            }
        }
        properties = {
            "recipientIndividual": {
                "$ref": "#/definitions/Person",
                "title": "Recipient Ind",
            }
        }
        self.assertEqual(
            field_title(properties, definitions, "recipientIndividual.id"),
            "Recipient Ind: Identifier",
        )

    def test_ref_to_a_scalar_keeps_the_definitions_title(self):
        definitions = {"currency": {"type": "string", "title": "Currency"}}
        properties = {"currency": {"$ref": "#/definitions/currency"}}
        self.assertEqual(field_title(properties, definitions, "currency"), "Currency")
