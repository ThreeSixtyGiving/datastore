from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection

from data_quality import quality_data
import db.models as db

from multiprocessing.dummy import Pool


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

        def process_source_file(source_file):
            try:
                grants_list = {
                    "grants": list(source_file.grant_set.values_list("data", flat=True))
                }
                source_file.quality, source_file.aggregate = quality_data.create(
                    grants_list
                )
                source_file.save()
            except Exception as e:
                print(
                    "Could not create source file quality data for %s"
                    % str(source_file)
                )
                print(e)

            connection.close()

        with Pool(4) as process_pool:
            process_pool.starmap(process_source_file, zip(source_files))

        def process_publishers(source_file):
            publisher = source_file.get_publisher()

            try:
                (
                    publisher.quality,
                    publisher.aggregate,
                ) = quality_data.create_publisher_stats(publisher)
                publisher.save()
            except Exception as e:
                print("Could not create publisher quality data for %s" % str(publisher))
                print(e)
            connection.close()

        with Pool(4) as process_pool:
            process_pool.starmap(
                process_publishers,
                zip(source_files.distinct("data__publisher__prefix")),
            )

        # Clear all caches - data has changed
        cache.clear()
