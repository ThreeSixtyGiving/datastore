from typing import Optional, Literal
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
        print(f"{e} Could not create source file data for: {source_file['pk']}")


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

        parser.add_argument(
            "--threads",
            type=int,
            default=3,
            help="Number of threads to use for processing quality data. Set to 0 to disable threading.",
        )

    def handle(self, *args, **options):
        getter_run: str = options["getter_run"]
        publisher_only: bool = options["publisher_only"]
        sourcefile_only: bool = options["sourcefile_only"]
        publisher_prefix: str | None = options.get("publisher")
        threads: int = options["threads"]

        rewrite_quality_data(
            getter_run=getter_run,
            publisher_only=publisher_only,
            sourcefile_only=sourcefile_only,
            publisher_prefix=publisher_prefix,
            threads=threads,
        )


def rewrite_quality_data(
    getter_run: str | Literal["latest"] = "latest",
    publisher_only: bool = False,
    sourcefile_only: bool = False,
    publisher_prefix: Optional[str] = None,
    threads: int = 0,
):
    if getter_run == "latest":
        source_files = db.Latest.objects.get(
            series=db.Latest.CURRENT
        ).sourcefile_set.all()
    else:
        source_files = db.SourceFile.objects.filter(getter_run=getter_run)

    if publisher_prefix:
        source_files = source_files.filter(data__publisher__prefix=publisher_prefix)

    publisher_objs_for_update = []
    sourcefile_objs_for_update = []

    if not publisher_only:
        print("Processing sourcefile quality data")
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

        try:
            if not threads:
                source_file_results = [
                    process_source_file(sf) for sf in process_sf_list
                ]

            else:
                with Pool(threads) as process_pool:
                    source_file_results = process_pool.map(
                        process_source_file, process_sf_list
                    )

            for source_file_result in source_file_results:
                if source_file_result is None:
                    continue

                sf = db.SourceFile.objects.get(pk=source_file_result["pk"])
                sf.quality = source_file_result["quality"]
                sf.aggregate = source_file_result["aggregate"]
                sourcefile_objs_for_update.append(sf)

            db.SourceFile.objects.bulk_update(
                sourcefile_objs_for_update, ["quality", "aggregate"], batch_size=10000
            )
        except Exception as e:
            print(f"Error generating quality data {e}")

    def process_publishers(source_file_: db.SourceFile):
        """Updates the publisher data with aggregates and quality data relating to their source files"""
        publisher = db.Publisher.objects.get(
            prefix=source_file_.data["publisher"]["prefix"]
        )
        print(f"Processing Publisher Quality for {publisher.prefix}")

        try:
            (
                publisher.quality,
                publisher.aggregate,
            ) = quality_data.create_publisher_stats(publisher)
            publisher_objs_for_update.append(publisher)
        except Exception as e:
            print("Could not create publisher quality data for %s" % str(publisher))
            print(e)
        if threads > 0:
            connection.close()  # ????

    if not sourcefile_only:
        print(
            f"Processing publisher quality data ({source_files.distinct('data__publisher__prefix').count()})"
        )
        if not threads:
            for sf_ in source_files.distinct("data__publisher__prefix"):
                process_publishers(sf_)
        else:
            with dummy.Pool(threads) as process_pool:
                process_pool.starmap(
                    process_publishers,
                    zip(source_files.distinct("data__publisher__prefix")),
                )

        db.Publisher.objects.bulk_update(
            publisher_objs_for_update, ["quality", "aggregate"], batch_size=10000
        )

    # Clear all caches - data has changed
    cache.clear()
