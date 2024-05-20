from django.core.management.base import BaseCommand

from additional_data.sources.imd_snapshot import IMDSnapshotSource


class Command(BaseCommand):
    help = "Imports IMD snapshot from the GitHub Repo"

    def handle(self, *args, **options):
        source = IMDSnapshotSource()
        source.import_imd_snapshot()
