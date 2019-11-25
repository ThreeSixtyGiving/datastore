from django.core.management import call_command
from django.test import TestCase
from io import StringIO
from tempfile import TemporaryDirectory
from tests.generate_testdata import generate_data
import db.models as db


class CustomMgmtCommandsTest(TestCase):
    """ Test custom management commands """
    fixtures = ['test_data.json']

    def test_create_datagetter_data(self):
        err_out = StringIO()
        with TemporaryDirectory() as tmpdir:
            call_command('create_datagetter_data', dir=tmpdir, stderr=err_out)
            self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")

    def test_delete_datagetter_data(self):
        err_out = StringIO()
        call_command('delete_datagetter_data', "--oldest", "--no-prompt", stderr=err_out)
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")
        self.assertEqual(db.GetterRun.objects.count(), 0)

    def test_list_datagetter_runs(self):
        out = StringIO()
        err_out = StringIO()
        call_command('list_datagetter_runs', stdout=out, stderr=err_out)
        self.assertIn("1 |", out.getvalue())
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")

    def test_load_datagetter_data(self):
        err_out = StringIO()
        with TemporaryDirectory() as tmpdir:
            generate_data(tmpdir)
            call_command('load_datagetter_data', tmpdir, stderr=err_out)
            self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")
            # 50 in the Fixture and 50 from generate_data
            self.assertEqual(db.Grant.objects.count(), 100)

    def test_set_status(self):
        err_out = StringIO()
        call_command("set_status", what="test", status="READY", stderr=err_out)
        self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")
        self.assertTrue(db.Status.objects.get(what="test"))