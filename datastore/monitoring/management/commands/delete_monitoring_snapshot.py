from django.core.management.base import BaseCommand
from monitoring.models import MonitoringSnapshot


class Command(BaseCommand):
    help = "List monitoring snapshots"

    def add_arguments(self, parser):
        parser.add_argument(
            type=int,
            action="store",
            dest="snapshot_id",
            help="The snapshot id to delete",
        )

    def handle(self, *args, **options):
        snapshot_id = options["snapshot_id"]
        snapshot = MonitoringSnapshot.objects.get(id=snapshot_id)
        deleted = snapshot.delete()
        print(f"{deleted}")
