import csv
import datetime
import glob
import json
import os
from tempfile import TemporaryDirectory

import requests_mock
from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TransactionTestCase

import db.models as db
from bulk_data.management.commands.generate_bulk_data_export import build_segments
from bulk_data.schema import ADDITIONAL_DATA_SCHEMA_PATH, SCHEMA_URL, field_title

with open(
    os.path.join(settings.BASE_DIR, "static", "360-giving-schema-1.3-jsonschema.json")
) as _fp:
    FAKE_GIVING_SCHEMA_RESPONSE = json.load(_fp)

with open(ADDITIONAL_DATA_SCHEMA_PATH) as _fp:
    ADDITIONAL_DATA_SCHEMA_PROPERTIES = json.load(_fp)["properties"]


def additional_data_title(path):
    """Column title for an additional_data path, derived the same way the
    command itself derives it - so a schema wording change doesn't also
    require a test update"""
    return field_title(ADDITIONAL_DATA_SCHEMA_PROPERTIES, {}, path)


def call_export_command(**options):
    with requests_mock.Mocker() as m:
        m.get(SCHEMA_URL, json=FAKE_GIVING_SCHEMA_RESPONSE)
        call_command("generate_bulk_data_export", **options)


class BuildSegmentsTest(SimpleTestCase):
    def test_returns_all_time_and_rolling_last_five_years(self):
        segments = build_segments(
            min_date=datetime.date(2010, 3, 4), today=datetime.date(2026, 11, 20)
        )
        self.assertEqual(
            segments,
            [
                ("360g-grants-all-time", datetime.date(2010, 3, 4)),
                ("360g-grants-last-5-years", datetime.date(2021, 1, 1)),
            ],
        )


class GenerateBulkDataExportCommandTest(TransactionTestCase):
    fixtures = ["test_data.json"]

    def setUp(self):
        grant = db.Latest.grants().first()
        grant.data["recipientOrganization"][0]["charityNumber"] = "1234567"
        grant.data["recipientOrganization"][0]["companyNumber"] = "7654321"
        grant.data["recipientOrganization"][0]["location"] = [
            {"name": "Westminster", "geoCode": "E09000033", "geoCodeType": "GSS"}
        ]
        grant.data["recipientIndividual"] = {"id": "ID-1", "name": "Jane Doe"}
        grant.data["grantProgramme"] = [
            {"code": "GP1", "title": "Programme One", "url": "https://example.com/gp1"}
        ]
        grant.data["fundingType"] = [{"code": "FT1", "title": "Core Funding"}]
        grant.additional_data["recipientOrgInfos"] = [
            {"id": "GB-COH-X", "name": "X Ltd", "organisationTypePrimary": "company"}
        ]
        grant.additional_data["TSGFundingOrgType"] = "Community Foundation"
        grant.additional_data["recipientRegionName"] = "London"
        grant.additional_data["recipientDistrictName"] = "Westminster"
        grant.save()
        self.enriched_grant = grant

    def test_generates_jsonl_and_curated_csv_for_all_time_and_last_five_years(self):
        with TemporaryDirectory() as tmpdir:
            call_export_command(output_dir=tmpdir)

            jsonl_files = sorted(glob.glob(os.path.join(tmpdir, "*.jsonl")))
            self.assertEqual(
                [os.path.basename(f) for f in jsonl_files],
                ["360g-grants-all-time.jsonl", "360g-grants-last-5-years.jsonl"],
            )

            all_time_path = os.path.join(tmpdir, "360g-grants-all-time.jsonl")
            total_rows = 0
            with open(all_time_path) as fp:
                for line in fp:
                    row = json.loads(line)
                    self.assertIn("id", row)
                    self.assertIn("additional_data", row)
                    total_rows += 1
            self.assertEqual(total_rows, db.Latest.grants().count())

            csv_path = os.path.join(tmpdir, "360g-grants-all-time.csv")
            with open(csv_path) as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual(len(rows), total_rows)

            enriched_row = next(
                r for r in rows if r["Identifier"] == self.enriched_grant.data["id"]
            )
            self.assertEqual(enriched_row["Recipient Org: Charity Number"], "1234567")
            self.assertEqual(enriched_row["Recipient Org: Company Number"], "7654321")
            self.assertEqual(
                enriched_row["Recipient Org: Location: Name"], "Westminster"
            )
            self.assertEqual(enriched_row["Recipient Ind: Identifier"], "ID-1")
            self.assertEqual(
                enriched_row["Grant Programme: URL"], "https://example.com/gp1"
            )
            self.assertEqual(enriched_row["Funding Type: Title"], "Core Funding")
            self.assertEqual(
                enriched_row[additional_data_title("TSGRecipientType")], "Organisation"
            )
            self.assertEqual(
                enriched_row[additional_data_title("recipientRegionName")], "London"
            )
            self.assertEqual(
                enriched_row[
                    additional_data_title("recipientOrgInfos.organisationTypePrimary")
                ],
                "company",
            )
            self.assertEqual(
                enriched_row[additional_data_title("TSGFundingOrgType")],
                "Community Foundation",
            )
            self.assertTrue(
                enriched_row[additional_data_title("GNCanonicalRecipientOrgId")]
            )

    def test_a_field_missing_for_every_grant_is_just_blank_not_an_error(self):
        for grant in db.Latest.grants().all():
            grant.additional_data.pop("TSGFundingOrgType", None)
            grant.save()

        title = additional_data_title("TSGFundingOrgType")
        with TemporaryDirectory() as tmpdir:
            call_export_command(output_dir=tmpdir)
            csv_path = os.path.join(tmpdir, "360g-grants-all-time.csv")
            with open(csv_path) as fp:
                reader = csv.DictReader(fp)
                self.assertIn(title, reader.fieldnames)
                for row in reader:
                    self.assertEqual(row[title], "")

    def test_only_the_first_item_of_multi_item_arrays_is_used(self):
        other_grant = db.Latest.grants().all()[1]
        other_grant.data["recipientOrganization"].append(
            {"id": "GB-COH-SECOND", "name": "Second Org"}
        )
        other_grant.data["recipientOrganization"][0]["location"] = [
            {"name": "Westminster", "geoCode": "E09000033", "geoCodeType": "GSS"},
            {"name": "Camden", "geoCode": "E09000007", "geoCodeType": "GSS"},
        ]
        other_grant.data["fundingOrganization"].append(
            {"id": "GB-COH-FUNDER2", "name": "Second Funder"}
        )
        other_grant.additional_data["recipientOrgInfos"] = [
            {"id": "GB-COH-X", "name": "X Ltd", "organisationTypePrimary": "company"},
            {"id": "GB-COH-Y", "name": "Y Ltd", "organisationTypePrimary": "charity"},
        ]
        other_grant.save()

        with TemporaryDirectory() as tmpdir:
            call_export_command(output_dir=tmpdir)
            csv_path = os.path.join(tmpdir, "360g-grants-all-time.csv")
            with open(csv_path) as fp:
                rows = list(csv.DictReader(fp))

        multi_row = next(r for r in rows if r["Identifier"] == other_grant.data["id"])
        self.assertEqual(multi_row["Recipient Org: Identifier"], "GB-COH-example-a")
        self.assertEqual(multi_row["Recipient Org: Location: Name"], "Westminster")
        self.assertEqual(multi_row["Funding Org: Identifier"], "GB-example-b")
        self.assertEqual(
            multi_row[
                additional_data_title("recipientOrgInfos.organisationTypePrimary")
            ],
            "company",
        )

    def test_last_five_years_excludes_old_grants_but_includes_recent_ones(self):
        old_grant = db.Latest.grants().last()
        old_grant.data["awardDate"] = "2003-05-01"
        old_grant.save()

        recent_grant = db.Latest.grants().all()[1]
        recent_grant.data["awardDate"] = (
            datetime.date.today() - datetime.timedelta(days=30)
        ).isoformat()
        recent_grant.save()

        with TemporaryDirectory() as tmpdir:
            call_export_command(output_dir=tmpdir)

            with open(os.path.join(tmpdir, "360g-grants-all-time.jsonl")) as fp:
                all_time_ids = {json.loads(line)["id"] for line in fp}
            with open(os.path.join(tmpdir, "360g-grants-last-5-years.jsonl")) as fp:
                last_five_years_ids = {json.loads(line)["id"] for line in fp}

        self.assertEqual(len(all_time_ids), db.Latest.grants().count())
        self.assertIn(old_grant.data["id"], all_time_ids)
        self.assertNotIn(old_grant.data["id"], last_five_years_ids)
        self.assertEqual(last_five_years_ids, {recent_grant.data["id"]})
