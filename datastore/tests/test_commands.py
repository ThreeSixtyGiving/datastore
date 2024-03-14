from io import StringIO
from tempfile import TemporaryDirectory
import os
import json

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase

import db.models as db


class CustomMgmtCommandsTest(TransactionTestCase):
    """Test custom management commands"""

    fixtures = ["test_data.json"]

    def test_create_and_load_data_package(self):
        err_out = StringIO()
        with TemporaryDirectory() as tmpdir:
            call_command("create_data_package", dir=tmpdir, stderr=err_out)
            self.assertEqual(
                len(err_out.getvalue()), 0, "Errors output by create command"
            )

            with open(os.path.join(tmpdir, "data_all.json")) as da_fp:
                json.load(da_fp)

            # Check the output json lines file by parsing the first line
            with open(os.path.join(tmpdir, "funders.jl")) as funders_fp:
                json.loads(funders_fp.readline().strip())

            # Check the output json lines file by parsing the first line
            with open(os.path.join(tmpdir, "recipients.jl")) as recipients_fp:
                json.loads(recipients_fp.readline().strip())

            call_command("load_data_package", tmpdir, stderr=err_out)
            self.assertEqual(
                len(err_out.getvalue()), 0, "Errors output by load command"
            )

    def test_delete_datagetter_data(self):
        """
        Test that delete_datagetter_data --oldest deletes a single GetterRun.
        """
        getterruns_count_before = db.GetterRun.objects.count()
        err_out = StringIO()
        call_command(
            "delete_datagetter_data",
            "--oldest",
            "--no-prompt",
            "--force-delete-in-use-data",
            stderr=err_out,
        )
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")
        self.assertEqual(db.GetterRun.objects.count(), getterruns_count_before - 1)

    def test_doesnt_delete_in_use_datagetter_data_oldest(self):
        """
        Test that delete_datagetter_data doesn't delete any in-use GetterRuns when not forced to.
        """
        in_use_pks_before = set(gr.pk for gr in db.GetterRun.objects.in_use())
        err_out = StringIO()
        call_command(
            "delete_datagetter_data",
            "--oldest",
            "--no-prompt",
            stderr=err_out,
        )
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")
        self.assertSetEqual(
            in_use_pks_before,
            set(gr.pk for gr in db.GetterRun.objects.all() if gr.is_in_use()),
        )

    def test_doesnt_delete_in_use_datagetter_data(self):
        """
        Test that there all in-use GetterRuns are retained after deleting --all-not-in-use.
        """
        in_use_pks_before = set(gr.pk for gr in db.GetterRun.objects.in_use())
        err_out = StringIO()
        call_command(
            "delete_datagetter_data",
            "--all-not-in-use",
            "--no-prompt",
            stderr=err_out,
        )
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")
        self.assertEqual(
            set(gr.pk for gr in db.GetterRun.objects.all()), in_use_pks_before
        )

    def test_delete_all_not_in_use_data(self):
        """
        Test that there are no not-in-use GetterRuns after deleting --all-not-in-use.
        """
        err_out = StringIO()
        call_command(
            "delete_datagetter_data",
            "--all-not-in-use",
            "--no-prompt",
            stderr=err_out,
        )
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")
        self.assertEqual(db.GetterRun.objects.not_in_use().count(), 0)

    def test_list_datagetter_runs(self):
        out = StringIO()
        err_out = StringIO()
        call_command("list_datagetter_runs", stdout=out, stderr=err_out)
        self.assertIn("1   |", out.getvalue())
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")

    def test_set_status(self):
        err_out = StringIO()
        call_command("set_status", what="test", status="READY", stderr=err_out)
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")
        self.assertTrue(db.Status.objects.get(what="test"))

    def test_set_status_list(self):
        err_out = StringIO()
        call_command("set_status", list=True, stderr=err_out)
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")

    def test_set_status_invalid(self):
        err_out = StringIO()
        call_command("set_status", list_options=True, stderr=err_out)
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")

    def test_set_status_no_options(self):
        err_out = StringIO()
        try:
            call_command("set_status", stderr=err_out)
        except CommandError as e:
            self.assertTrue("Not enough parameters" in str(e), "Unexpected exception")

        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")

    def test_archive_getter_run_no_options(self):
        err_out = StringIO()
        try:
            call_command("archive_getter_run", stderr=err_out)
        except CommandError as e:
            self.assertTrue(
                "No datagetter data specified" in str(e), "Unexpected exception"
            )

        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")

    def test_archive_getter_run(self):
        err_out = StringIO()
        initial_sourcefile_count = db.SourceFile.objects.count()
        initial_publisher_count = db.Publisher.objects.count()

        call_command("archive_getter_run", "--oldest", "--no-prompt", stderr=err_out)

        # This will throw an exception if there is more than one
        archived_getter_run = db.GetterRun.objects.get(archived=True)

        self.assertEqual(
            archived_getter_run.grant_set.count(),
            0,
            "Grants weren't deleted from archived getter run",
        )

        self.assertEqual(
            db.SourceFile.objects.count(),
            initial_sourcefile_count,
            "SourceFile count reduced unexpectedly",
        )
        self.assertEqual(
            db.Publisher.objects.count(),
            initial_publisher_count,
            "Publisher count reduced unexpectedly",
        )

    def test_rewrite_quality_data(self):
        err_out = StringIO()

        call_command("rewrite_quality_data", "latest", stderr=err_out)

        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")

    def test_list_entities(self):
        err_out = StringIO()

        call_command("manage_entities_data", ("--list", "recipient"), stderr=err_out)
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")

        call_command("manage_entities_data", ("--list", "funder"), stderr=err_out)
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")

    def test_rewrite_additional_data(self):
        err_out = StringIO()

        call_command("rewrite_additional_data", "latest", stderr=err_out)
        self.assertEqual(
            len(err_out.getvalue()),
            0,
            f"Errors output by command: {err_out.getvalue()}",
        )

        call_command(
            "rewrite_additional_data",
            "latest",
            "--data-sources",
            "tsg_recipient_type",
            stderr=err_out,
        )
        self.assertEqual(
            len(err_out.getvalue()),
            0,
            f"Errors output by command: {err_out.getvalue()}",
        )
