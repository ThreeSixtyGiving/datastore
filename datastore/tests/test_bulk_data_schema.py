import json
import os

import requests
import requests_mock
from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase

from bulk_data.schema import (
    GIVING_SCHEMA_CACHE_KEY,
    SCHEMA_URL,
    field_title,
    load_schemas,
)

with open(
    os.path.join(settings.BASE_DIR, "static", "360-giving-schema-1.3-jsonschema.json")
) as _fp:
    FAKE_GIVING_SCHEMA_RESPONSE = json.load(_fp)


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


class LoadSchemasCachingTest(SimpleTestCase):
    def setUp(self):
        cache.delete(GIVING_SCHEMA_CACHE_KEY)

    def tearDown(self):
        cache.delete(GIVING_SCHEMA_CACHE_KEY)

    def test_successful_fetch_populates_the_cache(self):
        with requests_mock.Mocker() as m:
            m.get(SCHEMA_URL, json=FAKE_GIVING_SCHEMA_RESPONSE)
            load_schemas()

        self.assertEqual(
            cache.get(GIVING_SCHEMA_CACHE_KEY), FAKE_GIVING_SCHEMA_RESPONSE
        )

    def test_falls_back_to_cached_schema_when_github_is_unreachable(self):
        cache.set(GIVING_SCHEMA_CACHE_KEY, FAKE_GIVING_SCHEMA_RESPONSE, timeout=None)

        with requests_mock.Mocker() as m:
            m.get(SCHEMA_URL, exc=requests.ConnectionError)
            grant_properties, definitions, _ = load_schemas()

        self.assertEqual(grant_properties, FAKE_GIVING_SCHEMA_RESPONSE["properties"])

    def test_raises_when_github_is_unreachable_and_nothing_is_cached(self):
        with requests_mock.Mocker() as m:
            m.get(SCHEMA_URL, exc=requests.ConnectionError)
            with self.assertRaises(requests.ConnectionError):
                load_schemas()
