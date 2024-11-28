from django.test import TestCase

from db.models import Publisher, Funder, SourceFile
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
)


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
        "last_downloaded_at",
        "valid",
    ]

    def test_gather_metrics(self):
        count_funder_metrics = FunderMetricsRecord.objects.count()
        count_publisher_metrics = PublisherMetricsRecord.objects.count()
        count_source_file_metrics = SourceFileMetricsRecord.objects.count()

        gather_metrics()

        self.assertGreater(FunderMetricsRecord.objects.count(), count_funder_metrics)
        self.assertGreater(
            PublisherMetricsRecord.objects.count(), count_publisher_metrics
        )
        self.assertGreater(
            SourceFileMetricsRecord.objects.count(), count_source_file_metrics
        )

    def test_publisher_metrics(self):
        values = publisher_metrics(Publisher.objects.last())

        for metric in self.publisher_metrics:
            self.assertIn(metric, values)
            self.assertIsNotNone(values[metric])

    def test_funder_metrics(self):
        values = funder_metrics(Funder.objects.last())

        for metric in self.funder_metrics:
            self.assertIn(metric, values)
            self.assertIsNotNone(values[metric])

    def test_source_file_metrics(self):
        values = source_file_metrics(SourceFile.objects.last())

        for metric in self.source_file_metrics:
            self.assertIn(metric, values)
            self.assertIsNotNone(values[metric])
