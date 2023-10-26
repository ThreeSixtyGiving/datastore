from django.test import TransactionTestCase

import db.models as db


class GetterRunTest(TransactionTestCase):
    fixtures = ["test_data.json"]

    def test_in_use(self):
        total_count = db.GetterRun.objects.all().count()
        in_use_count = db.GetterRun.all_in_use().count()
        not_in_use_count = db.GetterRun.all_not_in_use().count()

        self.assertLessEqual(in_use_count, total_count)
        self.assertLess(
            not_in_use_count, total_count
        )  # there should always be *some* in-use data
        self.assertEqual(in_use_count + not_in_use_count, total_count)
