import json
import os
from typing import Any, Dict, Tuple

import requests
from django.conf import settings
from django.core.cache import cache

SCHEMA_URL = "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/schema/360-giving-schema.json"
ADDITIONAL_DATA_SCHEMA_PATH = os.path.join(
    settings.BASE_DIR, "additional_data", "schema", "additional-data-schema.json"
)

GIVING_SCHEMA_CACHE_KEY = "bulk_data_giving_schema"


def _resolve_ref(node: Dict[str, Any], definitions: Dict[str, Any]) -> Dict[str, Any]:
    """Replace a $ref with its definition, keeping a sibling title if present"""
    if "$ref" not in node:
        return node
    resolved = definitions[node["$ref"].rsplit("/", 1)[-1]]
    return {**resolved, **{k: v for k, v in node.items() if k != "$ref"}}


def field_title(
    properties: Dict[str, Any], definitions: Dict[str, Any], path: str
) -> str:
    """Returns human readable field titles"""
    titles = []
    for part in path.split("."):
        node = _resolve_ref(properties[part], definitions)
        if node.get("title"):
            titles.append(node["title"])
        if node.get("type") == "array":
            node = _resolve_ref(node["items"], definitions)
        properties = node.get("properties", {})
    return ": ".join(titles)


def _load_giving_schema() -> Dict[str, Any]:
    """Fetches the schema from github, falling back to a cached copy"""
    try:
        response = requests.get(SCHEMA_URL, timeout=30)
        response.raise_for_status()
        giving_schema = response.json()
    except requests.RequestException:
        giving_schema = cache.get(GIVING_SCHEMA_CACHE_KEY)
        if giving_schema is None:
            raise
        return giving_schema

    cache.set(GIVING_SCHEMA_CACHE_KEY, giving_schema, timeout=None)
    return giving_schema


def load_schemas() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Loads both the standard schema and additional data schema"""
    giving_schema = _load_giving_schema()

    definitions = giving_schema.get("$defs") or giving_schema.get("definitions", {})

    with open(ADDITIONAL_DATA_SCHEMA_PATH) as fp:
        additional_data_schema = json.load(fp)

    return (
        giving_schema["properties"],
        definitions,
        additional_data_schema["properties"],
    )
