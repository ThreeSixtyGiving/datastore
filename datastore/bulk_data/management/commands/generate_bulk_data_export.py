import csv
import datetime
import json
import os
from typing import Any, Dict, List, Tuple

from django.core.management.base import BaseCommand, CommandError

from bulk_data.queries import (
    build_segments,
    get_award_date_range,
    stream_segment_to_jsonl,
)
from bulk_data.schema import field_title, load_schemas

GRANT_FIELDS = [
    "id",
    "title",
    "description",
    "currency",
    "amountAwarded",
    "awardDate",
    "plannedDates.startDate",
    "plannedDates.endDate",
    "plannedDates.duration",
    "recipientOrganization.id",
    "recipientOrganization.name",
    "recipientOrganization.charityNumber",
    "recipientOrganization.companyNumber",
    "recipientOrganization.postalCode",
    "recipientOrganization.location.geoCodeType",
    "recipientOrganization.location.geoCode",
    "recipientOrganization.location.name",
    "recipientIndividual.id",
    "recipientIndividual.name",
    "fundingOrganization.id",
    "fundingOrganization.name",
    "grantProgramme.code",
    "grantProgramme.title",
    "grantProgramme.url",
    "fundingType.title",
    "beneficiaryLocation.name",
    "beneficiaryLocation.geoCodeType",
    "beneficiaryLocation.geoCode",
    "dateModified",
]

ADDITIONAL_DATA_FIELDS = [
    "GNCanonicalRecipientOrgId",
    "GNCanonicalRecipientOrgName",
    "TSGRecipientType",
    "recipientOrgInfos.organisationTypePrimary",
    "TSGFundingOrgType",
    "recipientRegionName",
    "recipientDistrictName",
]


def _get_value(data: Dict[str, Any], path: str) -> Any:
    value = data
    for part in path.split("."):
        if isinstance(value, list):
            value = value[0] if value else {}
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value[0] if isinstance(value, list) and value else value


def build_curated_fields() -> List[Tuple[str, str, str]]:
    """Returns grant and additional data fields"""
    grant_properties, definitions, additional_data_properties = load_schemas()
    grant_fields = [
        (field_title(grant_properties, definitions, path), "row", path)
        for path in GRANT_FIELDS
    ]
    additional_fields = [
        (field_title(additional_data_properties, {}, path), "additional_data", path)
        for path in ADDITIONAL_DATA_FIELDS
    ]
    return grant_fields + additional_fields


def write_csv(
    jsonl_path: str, csv_path: str, fields: List[Tuple[str, str, str]]
) -> None:
    """Converts from JSONL to CSV"""
    with open(jsonl_path) as in_fp, open(csv_path, "w", newline="") as out_fp:
        writer = csv.writer(out_fp)
        writer.writerow([title for title, _, _ in fields])

        for line in in_fp:
            row = json.loads(line)
            sources = {"row": row, "additional_data": row.get("additional_data") or {}}
            writer.writerow(
                [_get_value(sources[root], path) for _, root, path in fields]
            )


def segment_name(start: datetime.date, end: datetime.date) -> str:
    return "360g-grants-%s-%s" % (start.year, end.year - 1)


class Command(BaseCommand):
    help = (
        "Extract all grants from the CURRENT Latest series "
        "into JSONL and CSV files segmented by 5 year awardDate ranges"
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--output-dir",
            action="store",
            dest="output_dir",
            type=str,
            help="Destination of the generated bulk data files",
            default="bulk_data_export",
        )

        parser.add_argument(
            "--segment-years",
            action="store",
            dest="segment_years",
            type=int,
            help="Number of years of awardDate covered by each output file",
            default=5,
        )

    def handle(self, **options: Any) -> None:
        output_dir = options["output_dir"]
        segment_years = options["segment_years"]
        os.makedirs(output_dir, exist_ok=True)

        min_date, max_date = get_award_date_range()
        if min_date is None:
            raise CommandError(
                "No grants with an awardDate found in the CURRENT Latest series"
            )

        segments = build_segments(min_date, max_date, segment_years)
        fields = build_curated_fields()

        for start, end in segments:
            name = segment_name(start, end)
            jsonl_path = os.path.join(output_dir, "%s.jsonl" % name)

            with open(jsonl_path, "w") as out_fp:
                count = stream_segment_to_jsonl(start, end, out_fp)
            self.stdout.write("%s: %s grants" % (name, count))

            if count == 0:
                continue

            csv_path = os.path.join(output_dir, "%s.csv" % name)
            write_csv(jsonl_path, csv_path, fields)
