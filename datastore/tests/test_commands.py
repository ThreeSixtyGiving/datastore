from io import StringIO
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

import db.models as db
from tests.generate_testdata import generate_data


class CustomMgmtCommandsTest(TestCase):
    """Test custom management commands"""

    fixtures = ["test_data.json"]

    def test_create_data_package(self):
        err_out = StringIO()
        with TemporaryDirectory() as tmpdir:
            call_command("create_data_package", dir=tmpdir, stderr=err_out)
            self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")

    def test_delete_datagetter_data(self):
        err_out = StringIO()
        call_command(
            "delete_datagetter_data", "--oldest", "--no-prompt", stderr=err_out
        )
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")
        self.assertEqual(db.GetterRun.objects.count(), 0)

    def test_list_datagetter_runs(self):
        out = StringIO()
        err_out = StringIO()
        call_command("list_datagetter_runs", stdout=out, stderr=err_out)
        self.assertIn("1 |", out.getvalue())
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")

    def test_load_datagetter_data(self):
        err_out = StringIO()
        with TemporaryDirectory() as tmpdir:
            generate_data(tmpdir)
            call_command("load_datagetter_data", tmpdir, stderr=err_out)
            self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")
            # 50 in the Fixture and 50 from generate_data
            self.assertEqual(db.Grant.objects.count(), 100)

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
