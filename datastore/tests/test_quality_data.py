from django.test import TestCase

from data_quality import quality_data
import db.models as db


class TestDataQualityData(TestCase):
    """Test creating data quality data"""

    fixtures = ["test_data.json"]

    def test_create_data_quality_data(self):
        grant = db.Grant.objects.first()
        quality = quality_data.create({"grants": [grant.data]})

        # Our test data in the test_data.json currently generates 3
        # data quality usefulness results
        self.assertEqual(len(quality), 3)
