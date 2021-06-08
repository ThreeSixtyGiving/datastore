from django.core.management.base import BaseCommand
from django.core import cache

from data_quality import quality_data
import db.models as db


class Command(BaseCommand):
    help = (
        "Reloads the additional data on grant data specified by datagetter id or latest"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            type=str,
            action="store",
            dest="getter_run",
            help="The datagetter run id or latest",
        )

    def handle(self, *args, **options):

        if "latest" in options["getter_run"]:
            source_files = db.Latest.objects.get(
                series=db.Latest.CURRENT
            ).sourcefile_set.all()
        else:
            source_files = db.SourceFile.objects.filter(
                getter_run=options["getter_run"]
            )

        for source_file in source_files:
            grants_list = {
                "grants": list(source_file.grant_set.values_list("data", flat=True))
            }
            source_file.quality, source_file.aggregate = quality_data.create(
                grants_list
            )
            source_file.save()

        # Clear all caches - data has changed
        cache.clear()
