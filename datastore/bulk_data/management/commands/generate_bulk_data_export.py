import csv
import datetime
import json
import os
from typing import Any, Dict, List, Tuple

from django.core.management.base import BaseCommand, CommandError

from bulk_data.queries import get_award_date_range, stream_segment_to_jsonl
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


def convert_jsonl_csv(
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


def build_segments(min_date: datetime.date, today: datetime.date):
    """Returns name and start_date pairs: one covering all time, one a rolling
    window of the last 5 calendar years"""
    return [
        ("360g-grants-all-time", min_date),
        ("360g-grants-last-5-years", datetime.date(today.year - 5, 1, 1)),
    ]


class Command(BaseCommand):
    help = (
        "Extract all grants from the CURRENT Latest series into JSONL and CSV "
        "files: one covering all time, one covering a rolling last 5 years"
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

    def handle(self, **options: Any) -> None:
        output_dir = options["output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        min_date, _ = get_award_date_range()
        if min_date is None:
            raise CommandError(
                "No grants with an awardDate found in the CURRENT Latest series"
            )

        segments = build_segments(min_date, datetime.date.today())
        fields = build_curated_fields()

        for name, start in segments:
            jsonl_path = os.path.join(output_dir, f"{name}.jsonl")

            with open(jsonl_path, "w") as out_fp:
                count = stream_segment_to_jsonl(start, None, out_fp)
            self.stdout.write(f"{name}: {count} grants")

            if count == 0:
                continue

            csv_path = os.path.join(output_dir, f"{name}.csv")
            convert_jsonl_csv(jsonl_path, csv_path, fields)
