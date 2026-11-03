import csv
import datetime
import glob
import json
import os
from tempfile import TemporaryDirectory

import requests_mock
from django.conf import settings
from django.core.management import call_command
from django.test import TransactionTestCase

import db.models as db
from bulk_data.queries import build_segments, get_award_date_range
from bulk_data.schema import SCHEMA_URL

with open(
    os.path.join(settings.BASE_DIR, "static", "360-giving-schema-1.3-jsonschema.json")
) as _fp:
    FAKE_GIVING_SCHEMA_RESPONSE = json.load(_fp)


def call_export_command(**options):
    with requests_mock.Mocker() as m:
        m.get(SCHEMA_URL, json=FAKE_GIVING_SCHEMA_RESPONSE)
        call_command("generate_bulk_data_export", **options)


class BuildSegmentsTest(TransactionTestCase):
    def test_single_segment(self):
        segments = build_segments(
            datetime.date(2019, 6, 1), datetime.date(2020, 1, 1), segment_years=5
        )
        self.assertEqual(
            segments, [(datetime.date(2019, 1, 1), datetime.date(2024, 1, 1))]
        )

    def test_spans_multiple_segments(self):
        segments = build_segments(
            datetime.date(2001, 3, 4), datetime.date(2012, 11, 1), segment_years=5
        )
        self.assertEqual(
            segments,
            [
                (datetime.date(2001, 1, 1), datetime.date(2006, 1, 1)),
                (datetime.date(2006, 1, 1), datetime.date(2011, 1, 1)),
                (datetime.date(2011, 1, 1), datetime.date(2016, 1, 1)),
            ],
        )

    def test_max_date_on_boundary_adds_new_segment(self):
        segments = build_segments(
            datetime.date(2015, 1, 1), datetime.date(2020, 1, 1), segment_years=5
        )
        self.assertEqual(
            segments,
            [
                (datetime.date(2015, 1, 1), datetime.date(2020, 1, 1)),
                (datetime.date(2020, 1, 1), datetime.date(2025, 1, 1)),
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

        min_date, max_date = get_award_date_range()
        self.segment_name = "360g-grants-%s-%s" % (
            min_date.year,
            min_date.year + 4,
        )

    def test_generates_jsonl_and_curated_csv_per_segment(self):
        with TemporaryDirectory() as tmpdir:
            call_export_command(output_dir=tmpdir)

            jsonl_files = sorted(glob.glob(os.path.join(tmpdir, "*.jsonl")))
            self.assertEqual(
                len(jsonl_files),
                1,
                "Expected one segment for the fixture's single-year data",
            )

            total_rows = 0
            with open(jsonl_files[0]) as fp:
                for line in fp:
                    row = json.loads(line)
                    self.assertIn("id", row)
                    self.assertIn("additional_data", row)
                    total_rows += 1
            self.assertEqual(total_rows, db.Latest.grants().count())

            csv_path = os.path.join(tmpdir, "%s.csv" % self.segment_name)
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
            self.assertEqual(enriched_row["360Giving Recipient Type"], "Organisation")
            self.assertEqual(enriched_row["Recipient Region Name"], "London")
            self.assertEqual(
                enriched_row["Recipient Org Info: Primary Organisation Type"],
                "company",
            )
            self.assertEqual(
                enriched_row["360Giving Funding Organisation Type"],
                "Community Foundation",
            )
            self.assertTrue(enriched_row["Recipient Org: Canonical Org ID"])

    def test_a_field_missing_for_every_grant_is_just_blank_not_an_error(self):
        for grant in db.Latest.grants().all():
            grant.additional_data.pop("TSGFundingOrgType", None)
            grant.save()

        with TemporaryDirectory() as tmpdir:
            call_export_command(output_dir=tmpdir)
            csv_path = os.path.join(tmpdir, "%s.csv" % self.segment_name)
            with open(csv_path) as fp:
                reader = csv.DictReader(fp)
                self.assertIn("360Giving Funding Organisation Type", reader.fieldnames)
                for row in reader:
                    self.assertEqual(row["360Giving Funding Organisation Type"], "")

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
            csv_path = os.path.join(tmpdir, "%s.csv" % self.segment_name)
            with open(csv_path) as fp:
                rows = list(csv.DictReader(fp))

        multi_row = next(r for r in rows if r["Identifier"] == other_grant.data["id"])
        self.assertEqual(multi_row["Recipient Org: Identifier"], "GB-COH-example-a")
        self.assertEqual(multi_row["Recipient Org: Location: Name"], "Westminster")
        self.assertEqual(multi_row["Funding Org: Identifier"], "GB-example-b")
        self.assertEqual(
            multi_row["Recipient Org Info: Primary Organisation Type"], "company"
        )

    def test_old_grant_goes_into_an_earlier_segment(self):
        old_grant = db.Latest.grants().last()
        old_grant.data["awardDate"] = "2003-05-01"
        old_grant.save()

        with TemporaryDirectory() as tmpdir:
            call_export_command(output_dir=tmpdir)
            jsonl_files = sorted(glob.glob(os.path.join(tmpdir, "*.jsonl")))

            self.assertGreater(len(jsonl_files), 1)

            old_segment_grant_ids = set()
            with open(jsonl_files[0]) as fp:
                for line in fp:
                    old_segment_grant_ids.add(json.loads(line)["id"])

        self.assertIn(old_grant.data["id"], old_segment_grant_ids)
        self.assertNotIn(self.enriched_grant.data["id"], old_segment_grant_ids)
