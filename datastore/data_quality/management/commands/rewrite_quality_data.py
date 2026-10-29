from typing import Any, Optional, Literal
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection, connections

from data_quality import quality_data
import db.models as db

from multiprocessing import Pool, dummy

# Variables to control batch sizes when re-writing sourcefile quality data.  In
# the future these could be added as command line arguments.
SOURCEFILE_QUALITY_DB_QUERY_CHUNK_SIZE = 10
SOURCEFILE_BULK_UPDATE_CHUNK_SIZE = 10
SOURCEFILE_IMAP_CHUNK_SIZE = 5


def process_source_file(source_file):
    try:
        sf = db.SourceFile.objects.get(pk=source_file["pk"])
        grants = list(sf.grant_set.values_list("data", flat=True))
        source_file_quality, source_file_aggregate = quality_data.create(grants)
        return {
            "pk": source_file["pk"],
            "identifier": source_file["identifier"],
            "quality": source_file_quality,
            "aggregate": source_file_aggregate,
        }
    except Exception as e:
        print(
            f"{e} Could not create source file data for: {source_file["identifier"]} (PK {source_file["pk"]})"
        )


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
    if not publisher_only:

        def get_source_files_list() -> dict[str, Any]:
            """Generator to query sourcefile records and return required data

            Yields
            ------
            dict[str, Any]
            """
            if getter_run == "latest":
                queryset = db.Latest.objects.get(
                    series=db.Latest.CURRENT
                ).sourcefile_set.iterator(chunk_size=10)
            else:
                queryset = db.SourceFile.objects.filter(getter_run=getter_run).iterator(
                    SOURCEFILE_QUALITY_DB_QUERY_CHUNK_SIZE
                )

            if publisher_prefix:
                queryset = queryset.filter(data__publisher__prefix=publisher_prefix)
            for source_file in queryset:
                yield {
                    "pk": source_file.pk,
                    "identifier": source_file.data["identifier"],
                }

        print("Processing sourcefile quality data ... ", end="", flush=True)

        try:
            source_files_to_process = [x for x in get_source_files_list()]

            if not threads:
                # Iterate over source file generator, process files, and add to list for updating.
                # When list reaches the maximum chunk size we update in the database and clear the list.
                sourcefile_objs_for_update = []
                for source_file in source_files_to_process:
                    print(
                        f"Rewriting quality data for source file {source_file['identifier']} ... ",
                        end="",
                    )
                    source_file_result = process_source_file(source_file)
                    sf = db.SourceFile(
                        id=source_file_result["pk"],
                        quality=source_file_result["quality"],
                        aggregate=source_file_result["aggregate"],
                    )
                    sourcefile_objs_for_update.append(sf)
                    print("done")
                    if (
                        len(sourcefile_objs_for_update)
                        > SOURCEFILE_BULK_UPDATE_CHUNK_SIZE
                    ):
                        db.SourceFile.objects.bulk_update(
                            sourcefile_objs_for_update, ["quality", "aggregate"]
                        )
                        sourcefile_objs_for_update.clear()

                # Do any final updates not done in the loop.
                db.SourceFile.objects.bulk_update(
                    sourcefile_objs_for_update, ["quality", "aggregate"]
                )

            else:

                def worker_init() -> None:
                    connections.close_all()

                # Each worker processes a chunk of source files returning an iterator.
                connection.close()
                with Pool(threads, initializer=worker_init) as process_pool:
                    source_file_results = process_pool.imap_unordered(
                        process_source_file,
                        source_files_to_process,
                        chunksize=SOURCEFILE_IMAP_CHUNK_SIZE,
                    )

                    # Loop over the iterators from each worker, generating database objects and adding
                    # them to a list for update.  When the list reaches it's maximum chunk size we
                    # update the database and clear the list.
                    sourcefile_objs_for_update = []
                    for source_file_result in source_file_results:
                        print(
                            f"Rewriting quality data for source file {source_file_result['identifier']} ... ",
                            end="",
                        )
                        sf = db.SourceFile(
                            id=source_file_result["pk"],
                            quality=source_file_result["quality"],
                            aggregate=source_file_result["aggregate"],
                        )
                        sourcefile_objs_for_update.append(sf)
                        print("done")
                        if (
                            len(sourcefile_objs_for_update)
                            > SOURCEFILE_BULK_UPDATE_CHUNK_SIZE
                        ):
                            db.SourceFile.objects.bulk_update(
                                sourcefile_objs_for_update, ["quality", "aggregate"]
                            )
                            sourcefile_objs_for_update.clear()

                    # Do any final updates not done in the loop.
                    db.SourceFile.objects.bulk_update(
                        sourcefile_objs_for_update, ["quality", "aggregate"]
                    )

        except Exception as e:
            print(f"error generating quality data {e}")

        print("done")

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

    publisher_objs_for_update = []
    if not sourcefile_only:
        # This code uses the original method of loading sourcefiles in that we load all of them at once.
        # This part of the code doesn't seem so memory hungry and so it is left as is.
        if getter_run == "latest":
            source_files = db.Latest.objects.get(
                series=db.Latest.CURRENT
            ).sourcefile_set.all()
        else:
            source_files = db.SourceFile.objects.filter(getter_run=getter_run)

        if publisher_prefix:
            source_files = source_files.filter(data__publisher__prefix=publisher_prefix)

        print(
            f"Processing publisher quality data for {source_files.distinct('data__publisher__prefix').count()} publishers ..."
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
