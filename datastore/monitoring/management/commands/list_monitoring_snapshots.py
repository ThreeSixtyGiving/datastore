from django.core.management.base import BaseCommand
from monitoring.models import MonitoringSnapshot, DatasetMetricsRecord, DatasetMetrics


class Command(BaseCommand):
    help = "List monitoring snapshots"

    def handle(self, *args, **options):
        for snapshot in MonitoringSnapshot.objects.all().order_by("-timestamp"):
            dataset_metrics = DatasetMetrics(
                **DatasetMetricsRecord.objects.get(snapshot=snapshot).metrics
            )
            print(
                f"{snapshot.id:5d}: {snapshot.timestamp.isoformat()} getter_run={snapshot.latest_getter_run_id} grants={dataset_metrics.total_grants} amount={dataset_metrics.total_amount_awarded_gbp}"
            )
