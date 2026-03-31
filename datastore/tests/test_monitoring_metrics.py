import csv
import copy
import io
from datetime import date, datetime, timedelta, timezone, UTC
import datetime as dt
from typing import Dict, Any, List, Optional
from django.urls import reverse
from rest_framework.test import APITestCase

from dataclasses import asdict
from django.test import TestCase

import faker

from db.models import (
    Publisher,
    Funder,
    SourceFile,
    Latest,
)
from monitoring.metrics import (
    gather_metrics,
    publisher_metrics,
    funder_metrics,
    source_file_metrics,
)
from monitoring.models import (
    PublisherMetricsRecord,
    FunderMetricsRecord,
    SourceFileMetricsRecord,
    DatasetMetricsRecord,
)
from monitoring.serializers import (
    PublisherMetricsRecordWithDownSourceFilesSerializerCSV,
)

from .fake_testdata import (
    fake_getter_run,
    fake_publisher_info,
    fake_sourcefile,
    fake_grant,
    copy_sourcefile,
    copy_grant,
    fake_grant_org,
)

TZ_BST_OFFSET = timezone(timedelta(hours=1))


class TestMonitoringMetricsQueries(APITestCase):
    # Things to test:
    # * Adding a new thing e.g. Publisher in a new GetterRun
    #    - Displayed when looking up new metrics
    #    - Doesn't crash when looking up old metrics, and old one shouldn't be displayed
    # * Removing a thing e.g. Funder
    #   - Should show all others with new timestamp, removed thing with old timestamp
    # * Get a snapshot for a specific day, not earlier or later values
    # * Get the latest values for a day where there are multiple GetterRuns for the same day
    # * A sourcefile goes down, increasing the timestamp difference, and comes back up again

    # Helper methods to get records

    def _get_records(
        self, what: str, snapshot_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        query_kwargs = {}
        if snapshot_date is not None:
            query_kwargs = {"snapshot_date": snapshot_date.isoformat()}

        url = reverse(f"api:{what}-metrics-snapshot", kwargs=query_kwargs)
        return self.client.get(url).json()

    def get_sourcefile_record(
        self, sourcefile_identifier: str, snapshot_date: Optional[date] = None
    ):
        """Helper method to get the metrics record for a given sourcefile via API"""
        sourcefile_records = self._get_records("source-file", snapshot_date)
        sourcefile_record = [
            sf
            for sf in sourcefile_records
            if sf["sourcefile_identifier"] == sourcefile_identifier
        ]
        # The metrics API should only ever return one record per SourceFile
        # ie. the most recent before the given timestamp (or latest if timestamp is None)
        self.assertEqual(len(sourcefile_record), 1)
        return sourcefile_record[0]

    def get_publisher_records(self, snapshot_date: Optional[date] = None):
        return self._get_records("publisher", snapshot_date)

    def get_funder_records(self, snapshot_date: Optional[date] = None):
        return self._get_records("funder", snapshot_date)

    def get_down_publishers(self, snapshot_date: Optional[date] = None):
        query_kwargs = {}
        if snapshot_date:
            query_kwargs = {"snapshot_date": snapshot_date.isoformat()}

        url = reverse("api:publisher-down-sourcefiles", kwargs=query_kwargs)
        response = self.client.get(url, headers={"Accept": "text/csv"})
        self.assertEqual(response.status_code, 200)
        response_content = response.content.decode("utf-8")

        def csv_row_to_list(csv_row: str) -> List[str]:
            row_reader = csv.reader([csv_row])
            return list(row_reader)[0]

        down_publishers = {}
        reader = csv.DictReader(io.StringIO(response_content))
        for row in reader:
            down_pub = copy.copy(row)
            # Handle the nested CSV rows / list values
            for (
                metric_name
            ) in (
                PublisherMetricsRecordWithDownSourceFilesSerializerCSV.SOURCE_FILE_NESTED_CSV_FIELDS
            ):
                down_pub[f"down_source_files.{metric_name}"] = csv_row_to_list(
                    down_pub[f"down_source_files.{metric_name}"]
                )

            down_publishers[down_pub["publisher_prefix"]] = down_pub

        return down_publishers

    def get_funder_change_records(self, from_: date, to_: date):
        url = reverse(
            "api:changed-funders",
            kwargs={"start_date": from_.isoformat(), "end_date": to_.isoformat()},
        )
        return self.client.get(url).json()

    # Test methods

    def test_new_publisher(self):
        # Check that:
        # * When a new GetterRun introduces a new Publisher, it appears in the new metrics snapshot
        # * and the old metrics snapshot still renders correctly
        fake = faker.Faker()

        funding_org = fake_grant_org(fake)
        recipient_org = fake_grant_org(fake)

        # Check that we start with no metrics snapshots
        self.assertEqual(PublisherMetricsRecord.objects.count(), 0)

        publisher_info_1 = fake_publisher_info(fake)
        publisher_info_2 = fake_publisher_info(fake)

        # Create first test GetterRun & Metrics
        with fake_getter_run(fake) as getter_run_1:
            sourcefile_1 = fake_sourcefile(
                fake, getter_run_1, publisher_info=publisher_info_1
            )
            fake_grant(
                fake,
                sourcefile=sourcefile_1,
                funder=funding_org,
                recipient=recipient_org,
            )

        # Check that we now have one Publisher
        start_num_publishers = len(self.get_publisher_records())
        self.assertEqual(start_num_publishers, 1)

        # Create second GetterRun, with old + new Publishers
        with fake_getter_run(fake) as getter_run_2:
            copy_sourcefile(
                fake,
                sourcefile=sourcefile_1,
                new_getter_run=getter_run_2,
                copy_grants=True,
            )

            sourcefile_2 = fake_sourcefile(fake, getter_run_2, publisher_info_2)
            fake_grant(
                fake,
                sourcefile=sourcefile_2,
                funder=funding_org,
                recipient=recipient_org,
            )

        # Check that the previous snapshot still has the same number of Publishers
        self.assertEqual(
            len(self.get_publisher_records(getter_run_1.datetime.date())),
            start_num_publishers,
        )

        # Check that the new snapshot has +1 Publishers
        self.assertEqual(
            len(self.get_publisher_records()),
            start_num_publishers + 1,
        )

    def test_sourcefile_downtime(self):
        # Create a Publisher with a SourceFile
        # The SourceFile will be down in the second GetterRun, then back up in the fourth
        # Check that the timestamp diff is as expected
        fake = faker.Faker()

        funding_org = fake_grant_org(fake)
        recipient_org = fake_grant_org(fake)
        test_publisher = fake_publisher_info(fake)

        # Check that we start with no metrics snapshots
        self.assertEqual(PublisherMetricsRecord.objects.count(), 0)
        self.assertEqual(SourceFileMetricsRecord.objects.all().count(), 0)

        # First GetterRun
        with fake_getter_run(fake) as getter_run_1:
            test_sourcefile = fake_sourcefile(
                fake, getter_run_1, test_publisher, valid=True, downloads=True
            )
            test_sourcefile_identifier = test_sourcefile.data["identifier"]
            test_grant = fake_grant(
                fake,
                sourcefile=test_sourcefile,
                funder=funding_org,
                recipient=recipient_org,
            )

        self.assertEqual(
            Latest.objects.get(series=Latest.CURRENT).sourcefile_set.count(), 1
        )
        self.assertEqual(SourceFileMetricsRecord.objects.all().count(), 1)

        # Check that the SourceFile is up
        self.assertEqual(
            self.get_sourcefile_record(test_sourcefile_identifier)["metrics"][
                "days_since_last_successful_download"
            ],
            0,
        )

        # Check that the Publisher doesn't appear in Unavailable Publishers
        self.assertNotIn(test_publisher["prefix"], self.get_down_publishers().keys())

        # Fake two days of sourcefile downtime
        # Run two GetterRuns (as they tend to be about 24 hours apart, but can be slightly less,
        # so it can still be less than 1 full day difference after just one)

        with fake_getter_run(fake) as getter_run_2:
            copy_sourcefile(
                fake,
                test_sourcefile,
                getter_run_2,
                downloads=False,
                valid=False,
                copy_grants=False,
            )

        with fake_getter_run(fake) as getter_run_3:
            copy_sourcefile(
                fake,
                test_sourcefile,
                getter_run_3,
                downloads=True,
                valid=False,
                copy_grants=False,
            )

        # Check that sourcefile is down
        # i.e. days_since_last_successful_download >= 1
        self.assertGreaterEqual(
            self.get_sourcefile_record(test_sourcefile_identifier)["metrics"][
                "days_since_last_successful_download"
            ],
            1,
        )

        # Check that the Publisher does now appear in Unavailable Publishers
        # along with the relevant SourceFile download URL
        down_publishers = self.get_down_publishers()
        self.assertIn(test_publisher["prefix"], down_publishers.keys())
        self.assertIn(
            test_sourcefile.data["distribution"][0]["downloadURL"],
            down_publishers[test_publisher["prefix"]][
                "down_source_files.last_download_attempt_download_url"
            ],
        )

        # Fake bringing the sourcefile back up
        with fake_getter_run(fake) as getter_run_4:
            test_sourcefile_4 = copy_sourcefile(
                fake,
                sourcefile=test_sourcefile,
                new_getter_run=getter_run_4,
                downloads=True,
                valid=True,
            )
            copy_grant(
                fake,
                grant=test_grant,
                new_getter_run=getter_run_4,
                new_sourcefile=test_sourcefile_4,
            )

        # Check that sourcefile back up
        self.assertEqual(
            self.get_sourcefile_record(test_sourcefile_identifier)["metrics"][
                "days_since_last_successful_download"
            ],
            0,
        )

    def test_fuzzy_day_counting(self):
        """
        Test that a day is counted even when getter runs are not strictly
        24 hours apart, but would roughly meet a human definition of "one day" passing.
        """
        fake = faker.Faker()

        funding_org = fake_grant_org(fake)
        recipient_org = fake_grant_org(fake)
        test_publisher = fake_publisher_info(fake)

        # First GetterRun
        with fake_getter_run(fake) as getter_run_1:
            test_sourcefile = fake_sourcefile(
                fake, getter_run_1, test_publisher, valid=True, downloads=True
            )
            test_sourcefile_identifier = test_sourcefile.data["identifier"]
            fake_grant(
                fake,
                sourcefile=test_sourcefile,
                funder=funding_org,
                recipient=recipient_org,
            )

        # Check that the SourceFile is up
        self.assertEqual(
            self.get_sourcefile_record(test_sourcefile_identifier)["metrics"][
                "days_since_last_successful_download"
            ],
            0,
        )

        # Fake a second getter run, where the getter runs are a bit less than a full 24 hours apart
        with fake_getter_run(fake, timestamp_dt=timedelta(hours=21)) as getter_run_2:
            copy_sourcefile(
                fake,
                test_sourcefile,
                getter_run_2,
                downloads=False,
                valid=False,
                copy_grants=False,
            )

        # Fake a third getter run, but later the same day - it shouldn't count as another day passing
        with fake_getter_run(fake, timestamp_dt=timedelta(hours=12)) as getter_run_3:
            copy_sourcefile(
                fake,
                test_sourcefile,
                getter_run_3,
                downloads=False,
                valid=False,
                copy_grants=False,
            )

        gr1_sf_metrics = SourceFileMetricsRecord.objects.get(
            publisher_prefix=test_publisher["prefix"],
            sourcefile_identifier=test_sourcefile.data["identifier"],
            timestamp=getter_run_1.datetime,
        )
        gr2_sf_metrics = SourceFileMetricsRecord.objects.get(
            publisher_prefix=test_publisher["prefix"],
            sourcefile_identifier=test_sourcefile.data["identifier"],
            timestamp=getter_run_2.datetime,
        )
        gr3_sf_metrics = SourceFileMetricsRecord.objects.get(
            publisher_prefix=test_publisher["prefix"],
            sourcefile_identifier=test_sourcefile.data["identifier"],
            timestamp=getter_run_3.datetime,
        )

        # Check that fuzzy day counting works
        # A little less than 24 hours between GR1 & GR2 counts as "one day"
        # but the significantly less than 24 hours between GR2 & GR3 doesn't
        self.assertEqual(
            gr1_sf_metrics.metrics["days_since_last_successful_download"] + 1,
            gr2_sf_metrics.metrics["days_since_last_successful_download"],
        )

        self.assertEqual(
            gr2_sf_metrics.metrics["days_since_last_successful_download"],
            gr3_sf_metrics.metrics["days_since_last_successful_download"],
        )

    def test_remove_funder(self):
        fake = faker.Faker()

        funder_a = fake_grant_org(fake)
        funder_b = fake_grant_org(fake)
        recipient = fake_grant_org(fake)
        test_publisher = fake_publisher_info(fake)

        # Create getter run containing two funders
        with fake_getter_run(fake) as getter_run_1:
            test_sourcefile = fake_sourcefile(
                fake, getter_run_1, publisher_info=test_publisher
            )
            test_grant_a = fake_grant(
                fake, sourcefile=test_sourcefile, funder=funder_a, recipient=recipient
            )
            fake_grant(
                fake, sourcefile=test_sourcefile, funder=funder_b, recipient=recipient
            )

        # Check that there are two Funders
        self.assertEqual(Funder.objects.count(), 2)
        funder_records_1 = self.get_funder_records()
        self.assertEqual(len(funder_records_1), 2)
        for funder_record in funder_records_1:
            self.assertEqual(
                datetime.fromisoformat(
                    # fromisoformat doesn't understand "Z" ending format to mean UTC until Py 3.11+
                    funder_record["timestamp"].rstrip("Z")
                ).astimezone(dt.timezone.utc),
                getter_run_1.datetime.astimezone(dt.timezone.utc),
            )

        # Create second getter run, removing a publisher
        with fake_getter_run(fake) as getter_run_2:
            test_sourcefile_2 = copy_sourcefile(
                fake, test_sourcefile, getter_run_2, copy_grants=False
            )
            copy_grant(fake, test_grant_a, getter_run_2, test_sourcefile_2)

        # Check that funder_b doesn't have a new record, only funder_a does
        self.assertEqual(Funder.objects.count(), 1)
        funder_records_2 = self.get_funder_records()
        self.assertEqual(len(funder_records_2), 2)
        for funder_record in funder_records_2:
            # funder a's record is new
            if funder_record["funder_org_id"] == funder_a["id"]:
                self.assertEqual(
                    datetime.fromisoformat(
                        # fromisoformat doesn't understand "Z" ending format to mean UTC until Py 3.11+
                        funder_record["timestamp"].rstrip("Z")
                    ).astimezone(dt.timezone.utc),
                    getter_run_2.datetime.astimezone(dt.timezone.utc),
                )

            elif funder_record["funder_org_id"] == funder_b["id"]:
                # funder b's record is old
                self.assertEqual(
                    datetime.fromisoformat(
                        # fromisoformat doesn't understand "Z" ending format to mean UTC until Py 3.11+
                        funder_record["timestamp"].rstrip("Z")
                    ).astimezone(dt.timezone.utc),
                    getter_run_1.datetime.astimezone(dt.timezone.utc),
                )

            else:
                # This should not happen, there should only be two records
                self.assertTrue(False)

    def test_funder_change_detection(self):
        fake = faker.Faker()

        # This test simulates five days of pipeline runs, changing the funders and checking that the changes
        # are reflected by the change monitoring endpoints.
        #
        # Day 1 creates the base case: 1 funder with 1 grant
        # Day 2 is identical to Day 1, check that no changes are output
        # Day 3 adds a second funder, checks that a new funder change is output
        # Day 4 removes a funder, checks that a removed funder change is output
        # Day 5 adds a second grant to the funder, checks that the change to total_grants and total_gbp are output

        funder_a = fake_grant_org(fake)
        funder_b = fake_grant_org(fake)
        recipient = fake_grant_org(fake)
        test_publisher = fake_publisher_info(fake)

        # Create getter run containing one funder
        with fake_getter_run(fake) as getter_run_1:
            sourcefile_a = fake_sourcefile(
                fake, getter_run_1, publisher_info=test_publisher
            )
            fake_grant(
                fake, sourcefile=sourcefile_a, funder=funder_a, recipient=recipient
            )

        # Extra getter run to ensure 2 days have passed before starting the tests
        with fake_getter_run(fake) as getter_run_2:
            copy_sourcefile(fake, sourcefile_a, getter_run_2, copy_grants=True)

        # Check that there is one Funder
        self.assertEqual(Funder.objects.count(), 1)

        ## Test that no change records are detected when nothing has changed
        self.assertEqual(
            len(
                self.get_funder_change_records(
                    from_=getter_run_1.datetime.date(), to_=getter_run_2.datetime.date()
                )
            ),
            0,
        )

        ## Test adding a new funder
        with fake_getter_run(fake) as getter_run_3:
            copy_sourcefile(fake, sourcefile_a, getter_run_3, copy_grants=True)
            sourcefile_b = fake_sourcefile(
                fake, getter_run_3, publisher_info=test_publisher
            )
            fake_grant(fake, sourcefile_b, funder_b, recipient=recipient)

        funder_change_records = self.get_funder_change_records(
            from_=getter_run_2.datetime.date(), to_=getter_run_3.datetime.date()
        )
        self.assertEqual(len(funder_change_records), 1)
        self.assertEqual(
            funder_change_records[0]["end_record"]["funder_org_id"], funder_b["id"]
        )
        self.assertIsNone(funder_change_records[0]["start_record"])
        self.assertTrue(funder_change_records[0]["record_is_new"])
        self.assertFalse(funder_change_records[0]["record_was_removed"])

        ## Test removing a funder
        with fake_getter_run(fake) as getter_run_4:
            # don't copy sourcefile_a => dropped funder A
            copy_sourcefile(fake, sourcefile_b, getter_run_4, copy_grants=True)

        funder_change_records = self.get_funder_change_records(
            from_=getter_run_3.datetime.date(), to_=getter_run_4.datetime.date()
        )
        self.assertEqual(len(funder_change_records), 1)
        self.assertEqual(
            funder_change_records[0]["start_record"]["funder_org_id"], funder_a["id"]
        )
        self.assertIsNone(funder_change_records[0]["end_record"])
        self.assertFalse(funder_change_records[0]["record_is_new"])
        self.assertTrue(funder_change_records[0]["record_was_removed"])

        ## Test changing a couple of a funder's metrics
        with fake_getter_run(fake) as getter_run_5:
            sourcefile_b_5 = copy_sourcefile(
                fake, sourcefile_b, getter_run_5, copy_grants=True
            )
            # Add another grant to change funder's total_grants and total_gbp
            fake_grant(fake, sourcefile_b_5, funder_b, recipient)

        funder_change_records = self.get_funder_change_records(
            from_=getter_run_4.datetime.date(), to_=getter_run_5.datetime.date()
        )
        self.assertEqual(len(funder_change_records), 1)
        self.assertEqual(
            funder_change_records[0]["start_record"]["funder_org_id"], funder_b["id"]
        )
        self.assertEqual(
            funder_change_records[0]["start_record"]["metrics"]["total_grants"], 1
        )
        self.assertEqual(
            funder_change_records[0]["end_record"]["metrics"]["total_grants"], 2
        )
        self.assertIn("total_grants", funder_change_records[0]["changed_metrics"])
        self.assertIn("total_gbp", funder_change_records[0]["changed_metrics"])
        self.assertFalse(funder_change_records[0]["record_is_new"])
        self.assertFalse(funder_change_records[0]["record_was_removed"])

    def test_funder_change_detection_into_bst(self):
        # This test simulates four days of pipeline runs from UTC to BST.

        # Day 1: UTC: creates the base case: 2 funders with 1 grant each
        # Day 2: UTC: identical, should have no changes.
        # Day 3: BST: add a second grant to funder 2, this chould generate a change to total_grants and total_gbp
        # Day 4: BST: identical, should have no changes.

        fake = faker.Faker()
        funder_a = fake_grant_org(fake)
        funder_b = fake_grant_org(fake)
        recipient = fake_grant_org(fake)
        test_publisher = fake_publisher_info(fake)

        # Create two getter runs with two funders and in UTC.
        with fake_getter_run(
            fake, timestamp=datetime(2026, 3, 28, 0, 10, 0, tzinfo=UTC)
        ) as getter_run_1:
            sourcefile_a = fake_sourcefile(
                fake, getter_run_1, publisher_info=test_publisher
            )
            sourcefile_b = fake_sourcefile(
                fake, getter_run_1, publisher_info=test_publisher
            )
            fake_grant(
                fake, sourcefile=sourcefile_a, funder=funder_a, recipient=recipient
            )
            fake_grant(
                fake, sourcefile=sourcefile_b, funder=funder_b, recipient=recipient
            )

        with fake_getter_run(
            fake, timestamp=datetime(2026, 3, 29, 0, 10, 0, tzinfo=UTC)
        ) as getter_run_2:
            copy_sourcefile(fake, sourcefile_a, getter_run_2, copy_grants=True)
            copy_sourcefile(fake, sourcefile_b, getter_run_2, copy_grants=True)

        # Test that no change records are detected when nothing has changed
        self.assertEqual(
            len(
                self.get_funder_change_records(
                    from_=date(2026, 3, 28), to_=date(2026, 3, 29)
                )
            ),
            0,
        )

        # Getter run, now in BST, add a second grant.
        with fake_getter_run(
            fake, timestamp=datetime(2026, 3, 30, 0, 10, 0, tzinfo=TZ_BST_OFFSET)
        ) as getter_run_3:
            copy_sourcefile(fake, sourcefile_a, getter_run_3, copy_grants=True)

            # # Add second grant to funder b.
            sourcefile_b_3 = copy_sourcefile(
                fake, sourcefile_b, getter_run_3, copy_grants=True
            )
            fake_grant(fake, sourcefile_b_3, funder_b, recipient)

        # Test that there is only one change record and no removal record.
        funder_change_records = self.get_funder_change_records(
            from_=date(2026, 3, 29), to_=date(2026, 3, 30)
        )
        self.assertEqual(len(funder_change_records), 1)
        self.assertEqual(
            funder_change_records[0]["start_record"]["funder_org_id"], funder_b["id"]
        )
        self.assertEqual(
            funder_change_records[0]["start_record"]["metrics"]["total_grants"], 1
        )
        self.assertEqual(
            funder_change_records[0]["end_record"]["metrics"]["total_grants"], 2
        )
        self.assertIn("total_grants", funder_change_records[0]["changed_metrics"])
        self.assertIn("total_gbp", funder_change_records[0]["changed_metrics"])
        self.assertFalse(funder_change_records[0]["record_is_new"])
        self.assertFalse(funder_change_records[0]["record_was_removed"])

        # Test final step, in BST.
        with fake_getter_run(
            fake, timestamp=datetime(2026, 3, 31, 0, 10, 0, tzinfo=TZ_BST_OFFSET)
        ) as getter_run_4:
            copy_sourcefile(fake, sourcefile_a, getter_run_4, copy_grants=True)
            copy_sourcefile(fake, sourcefile_b_3, getter_run_4, copy_grants=True)

        ## Test that no change records are detected when nothing has changed
        self.assertEqual(
            len(
                self.get_funder_change_records(
                    from_=date(2026, 3, 30), to_=date(2026, 3, 31)
                )
            ),
            0,
        )

    def test_funder_change_detection_from_bst(self):
        # This test simulates four days of pipeline runs from BST to UTC. to BST.

        # Day 1: BST: creates the base case: 2 funders with 1 grant each
        # Day 2: BST: identical, should have no changes.
        # Day 3: UTC: add a second grant to funder 2, this chould generate a change to total_grants and total_gbp
        # Day 4: UTC: identical, should have no changes.

        fake = faker.Faker()
        funder_a = fake_grant_org(fake)
        funder_b = fake_grant_org(fake)
        recipient = fake_grant_org(fake)
        test_publisher = fake_publisher_info(fake)

        # Create two getter runs with two funders and in BST.
        with fake_getter_run(
            fake, timestamp=datetime(2026, 10, 24, 0, 10, 0, tzinfo=TZ_BST_OFFSET)
        ) as getter_run_1:
            sourcefile_a = fake_sourcefile(
                fake, getter_run_1, publisher_info=test_publisher
            )
            sourcefile_b = fake_sourcefile(
                fake, getter_run_1, publisher_info=test_publisher
            )
            fake_grant(
                fake, sourcefile=sourcefile_a, funder=funder_a, recipient=recipient
            )
            fake_grant(
                fake, sourcefile=sourcefile_b, funder=funder_b, recipient=recipient
            )

        with fake_getter_run(
            fake, timestamp=datetime(2026, 10, 25, 0, 10, 0, tzinfo=TZ_BST_OFFSET)
        ) as getter_run_2:
            copy_sourcefile(fake, sourcefile_a, getter_run_2, copy_grants=True)
            copy_sourcefile(fake, sourcefile_b, getter_run_2, copy_grants=True)

        # Test that no change records are detected when nothing has changed
        self.assertEqual(
            len(
                self.get_funder_change_records(
                    from_=date(2026, 10, 24), to_=date(2026, 10, 25)
                )
            ),
            0,
        )

        # Getter run, now in BST, add a second grant.
        with fake_getter_run(
            fake, timestamp=datetime(2026, 10, 26, 0, 10, 0, tzinfo=UTC)
        ) as getter_run_3:
            copy_sourcefile(fake, sourcefile_a, getter_run_3, copy_grants=True)

            # # Add second grant to funder b.
            sourcefile_b_3 = copy_sourcefile(
                fake, sourcefile_b, getter_run_3, copy_grants=True
            )
            fake_grant(fake, sourcefile_b_3, funder_b, recipient)

        # Test that there is only one change record and no removal record.
        funder_change_records = self.get_funder_change_records(
            from_=date(2026, 10, 25), to_=date(2026, 10, 26)
        )
        self.assertEqual(len(funder_change_records), 1)
        self.assertEqual(
            funder_change_records[0]["start_record"]["funder_org_id"], funder_b["id"]
        )
        self.assertEqual(
            funder_change_records[0]["start_record"]["metrics"]["total_grants"], 1
        )
        self.assertEqual(
            funder_change_records[0]["end_record"]["metrics"]["total_grants"], 2
        )
        self.assertIn("total_grants", funder_change_records[0]["changed_metrics"])
        self.assertIn("total_gbp", funder_change_records[0]["changed_metrics"])
        self.assertFalse(funder_change_records[0]["record_is_new"])
        self.assertFalse(funder_change_records[0]["record_was_removed"])

        # Test final step, in BST.
        with fake_getter_run(
            fake, timestamp=datetime(2026, 10, 27, 0, 10, 0, tzinfo=UTC)
        ) as getter_run_4:
            copy_sourcefile(fake, sourcefile_a, getter_run_4, copy_grants=True)
            copy_sourcefile(fake, sourcefile_b_3, getter_run_4, copy_grants=True)

        ## Test that no change records are detected when nothing has changed
        self.assertEqual(
            len(
                self.get_funder_change_records(
                    from_=date(2026, 10, 26), to_=date(2026, 10, 27)
                )
            ),
            0,
        )

    def test_multiple_getterruns_in_one_day(self):
        """
        When there are multiple getter runs in one day, the snapshot api should show only the most recent.
        """
        fake = faker.Faker()

        funder = fake_grant_org(fake)
        recipient = fake_grant_org(fake)
        test_publisher = fake_publisher_info(fake)

        # Random datetime at least 30 days ago
        getter_run_1_datetime = fake.date_time(
            end_datetime="-30d", tzinfo=dt.timezone.utc
        )
        # The second getter run below is created 4 hours after the first, so we need to ensure there are at least 4 more
        # hours in the same day after the first getter run.
        if getter_run_1_datetime.hour > 19:
            getter_run_1_datetime = getter_run_1_datetime.replace(hour=19)

        with fake_getter_run(fake, timestamp=getter_run_1_datetime) as getter_run_1:
            test_sourcefile = fake_sourcefile(
                fake, getter_run_1, publisher_info=test_publisher
            )
            fake_grant(
                fake,
                sourcefile=test_sourcefile,
                funder=funder,
                recipient=recipient,
                amount_awarded=100,
            )

        with fake_getter_run(
            fake, timestamp=getter_run_1.datetime + timedelta(hours=4)
        ) as getter_run_2:
            test_sourcefile_2 = copy_sourcefile(
                fake, test_sourcefile, getter_run_2, copy_grants=False
            )
            fake_grant(
                fake,
                sourcefile=test_sourcefile_2,
                funder=funder,
                recipient=recipient,
                # Change amount awarded
                amount_awarded=200,
            )

        funder_records = self.get_funder_records(
            snapshot_date=getter_run_1.datetime.date()
        )
        self.assertEqual(len(funder_records), 1)
        self.assertEqual(funder_records[0]["metrics"]["total_gbp"], 200)

    def test_non_gbp_currencies(self):
        fake = faker.Faker()

        funder = fake_grant_org(fake)
        recipient = fake_grant_org(fake)
        test_publisher = fake_publisher_info(fake)

        # Create a publisher with a couple of non-GBP grants
        with fake_getter_run(fake) as getter_run_1:
            sourcefile = fake_sourcefile(fake, getter_run_1, test_publisher)
            fake_grant(fake, sourcefile, funder, recipient, currency="EUR")
            fake_grant(fake, sourcefile, funder, recipient, currency="USD")

        # Check that non-GBP amounts are reflected in monitoring metrics
        # and that GBP totals should be zero given there are no GBP grants
        dataset_metrics = DatasetMetricsRecord.objects.all()[0]
        self.assertFalse(dataset_metrics.metrics.get("total_amount_awarded_gbp"))
        self.assertGreater(dataset_metrics.metrics["total_amount_awarded_eur"], 0)
        self.assertGreater(dataset_metrics.metrics["total_amount_awarded_usd"], 0)

        publisher_metrics = PublisherMetricsRecord.objects.all()[0]
        self.assertFalse(publisher_metrics.metrics.get("total_gbp"))
        self.assertGreater(publisher_metrics.metrics["total_eur"], 0)
        self.assertGreater(publisher_metrics.metrics["total_usd"], 0)

        funder_metrics = FunderMetricsRecord.objects.all()[0]
        self.assertFalse(funder_metrics.metrics.get("total_gbp"))
        self.assertGreater(funder_metrics.metrics["total_eur"], 0)
        self.assertGreater(funder_metrics.metrics["total_usd"], 0)


class TestMonitoringMetrics(TestCase):
    fixtures = ["test_data.json"]

    publisher_metrics = [
        "total_grants",
        "total_gbp",
        "total_funders",
        "total_recipient_individuals",
        "total_recipient_organisations",
    ]

    funder_metrics = [
        "total_grants",
        "total_gbp",
        "latest_award_date",
        "earliest_award_date",
    ]

    source_file_metrics = [
        "last_successful_download_at",
        "last_download_attempt_at",
        "last_download_attempt_downloaded",
        "last_download_attempt_valid",
        "last_download_attempt_error",
        "days_since_last_successful_download",
        "last_download_attempt_download_url",
        "last_download_attempt_access_url",
        "last_successful_download_was_at_least_7_days_ago",
    ]

    def test_gather_metrics(self):
        count_dataset_metrics = DatasetMetricsRecord.objects.count()
        count_funder_metrics = FunderMetricsRecord.objects.count()
        count_publisher_metrics = PublisherMetricsRecord.objects.count()
        count_source_file_metrics = SourceFileMetricsRecord.objects.count()

        gather_metrics()

        self.assertEqual(
            DatasetMetricsRecord.objects.count(), count_dataset_metrics + 1
        )
        self.assertGreater(FunderMetricsRecord.objects.count(), count_funder_metrics)
        self.assertGreater(
            PublisherMetricsRecord.objects.count(), count_publisher_metrics
        )
        self.assertGreater(
            SourceFileMetricsRecord.objects.count(), count_source_file_metrics
        )

    def test_publisher_metrics(self):
        for publisher in Publisher.objects.all():
            values = asdict(publisher_metrics(publisher))

            for metric in self.publisher_metrics:
                self.assertIn(metric, values)

    def test_funder_metrics(self):
        for funder in Funder.objects.all():
            values = asdict(funder_metrics(funder))

            for metric in self.funder_metrics:
                self.assertIn(metric, values)

    def test_source_file_metrics(self):
        for source_file in SourceFile.objects.all():
            values = asdict(source_file_metrics(source_file))

            for metric in self.source_file_metrics:
                self.assertIn(metric, values)
