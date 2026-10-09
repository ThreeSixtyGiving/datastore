#!/usr/bin/env bash
# Regenerates the JSON Schema / OpenAPI 3.0 copies served from this directory
# and used by the API docs (drf-spectacular's $ref targets).
#
# Usage:
#   ./update_schemas.sh                   # refresh the additional data schema only
#   ./update_schemas.sh 1.4                # also fetch & refresh the 360G grant schema at version 1.4
#
set -euo pipefail

cd "$(dirname "$0")"

CONVERT=(npx --yes @openapi-contrib/json-schema-to-openapi-schema convert)

echo "Regenerating additional data schema..."
cp ../additional_data/schema/additional-data-schema.json additional-data-schema-jsonschema.json
"${CONVERT[@]}" additional-data-schema-jsonschema.json > additional-data-schema-openapi.json

if [ "${1:-}" != "" ]; then
    STANDARD_VERSION="$1"
    echo "Fetching 360G grant schema ${STANDARD_VERSION} from ThreeSixtyGiving/standard..."
    JSONSCHEMA_FILE="360-giving-schema-${STANDARD_VERSION}-jsonschema.json"
    curl -sSf "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/${STANDARD_VERSION}/schema/360-giving-schema.json" \
        -o "${JSONSCHEMA_FILE}.tmp"
    mv "${JSONSCHEMA_FILE}.tmp" "${JSONSCHEMA_FILE}"
    "${CONVERT[@]}" "${JSONSCHEMA_FILE}" > "360-giving-schema-${STANDARD_VERSION}-openapi.json"
    echo "Update TSG_OPENAPI_SCHEMA_STATICFILE in settings.py to point at version ${STANDARD_VERSION}."
fi