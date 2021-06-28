from io import StringIO
import json
import os
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TransactionTestCase

import db.models as db
from tests.generate_testdata import generate_data


class LatestDataTest(TransactionTestCase):
    def break_the_data(self, tmpdir):
        data_all_path = os.path.join(tmpdir, "data_all.json")
        dataset = None

        with open(data_all_path) as data_all_fp:
            dataset = json.load(data_all_fp)

            for i, ob in enumerate(dataset):
                # Make half the data fail download
                if i % 2:
                    ob["datagetter_metadata"]["downloads"] = False
                    ob["datagetter_metadata"]["json"] = None

        with open(data_all_path, "w") as data_all_fp:
            json.dump(dataset, data_all_fp)

    def test_latest_data(self):
        err_out = StringIO()
        with TemporaryDirectory() as tmpdir:
            generate_data(tmpdir)
            # Load the good data
            call_command("load_datagetter_data", tmpdir, stderr=err_out)
            self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")
            # 50 in the Fixture and 50 from generate_data
            self.assertEqual(db.Grant.objects.count(), 50)
            self.assertEqual(
                db.Latest.objects.get(series=db.Latest.CURRENT).grant_set.count(), 50
            )
            # Load broken data - This should trigger fall back mechanism
            print("Breaking the data")
            self.break_the_data(tmpdir)

            call_command("load_datagetter_data", tmpdir, stderr=err_out)
            self.assertEqual(len(err_out.getvalue()), 0, "Errors output by command")

            self.assertEqual(
                db.Latest.objects.get(series=db.Latest.CURRENT).grant_set.count(), 50
            )
