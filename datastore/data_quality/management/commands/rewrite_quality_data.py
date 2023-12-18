from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection

from data_quality import quality_data
import db.models as db

from multiprocessing import Pool, dummy


def process_source_file(source_file):
    try:
        source_file["quality"], source_file["aggregate"] = quality_data.create(
            source_file["grants"]
        )
        return source_file
    except Exception as e:
        print(f"{e} Could not create source file data for: {source_file}")


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

        parser.add_argument(
            "--publisher-only",
            action="store_true",
            help="Only rewrite publisher data",
        )

        parser.add_argument(
            "--sourcefile-only",
            action="store_true",
            help="Only rewrite sourcefile data",
        )

        parser.add_argument(
            "--publisher",
            action="store",
            dest="publisher",
            help="Update the quality data for specified publisher (prefix)",
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

        if options.get("publisher"):
            source_files = source_files.filter(
                data__publisher__prefix=options["publisher"]
            )

        publisher_objs_for_update = []
        sourcefile_objs_for_update = []

        if not options["publisher_only"]:
            print("Processing sourcefile data")
            process_sf_list = []
            for source_file in source_files:
                process_sf_list.append(
                    {
                        "pk": source_file.pk,
                        "grants": list(
                            source_file.grant_set.values_list("data", flat=True)
                        ),
                    }
                )

            with Pool(8) as process_pool:
                source_file_results = process_pool.map(
                    process_source_file, process_sf_list
                )

                for source_file_result in source_file_results:
                    sf = db.SourceFile.objects.get(pk=source_file_result["pk"])
                    sf.quality = source_file_result["quality"]
                    sf.aggregate = source_file_result["aggregate"]
                    sourcefile_objs_for_update.append(sf)

            db.SourceFile.objects.bulk_update(
                sourcefile_objs_for_update, ["quality", "aggregate"], batch_size=10000
            )

        def process_publishers(source_file):
            publisher = source_file.get_publisher()

            print(publisher)

            try:
                (
                    publisher.quality,
                    publisher.aggregate,
                ) = quality_data.create_publisher_stats(publisher)
                publisher_objs_for_update.append(publisher)
            except Exception as e:
                print("Could not create publisher quality data for %s" % str(publisher))
                print(e)
            connection.close()

        if not options["sourcefile_only"]:
            print("Processing publisher data")
            with dummy.Pool(4) as process_pool:
                process_pool.starmap(
                    process_publishers,
                    zip(source_files.distinct("data__publisher__prefix")),
                )

            db.Publisher.objects.bulk_update(
                publisher_objs_for_update, ["quality", "aggregate"], batch_size=10000
            )

        # Clear all caches - data has changed
        cache.clear()
