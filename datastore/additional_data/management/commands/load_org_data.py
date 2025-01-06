from django.core.management import CommandError
from django.core.management.base import BaseCommand
from django.db import transaction

from additional_data.models import OrgInfoCache
from additional_data.sources.find_that_charity import FindThatCharitySource, FTC_SOURCES


class Command(BaseCommand):
    help = "Import org info from find that charity data sources"

    def add_arguments(self, parser):
        parser.add_argument(
            type=str,
            nargs="?",
            action="store",
            dest="path",
            help="The location or url of the csv file",
        )

        parser.add_argument(
            type=str,
            nargs="?",
            action="store",
            dest="org_type",
            help="Which org source this data is from will guess from path if not supplied, Options %s"
            % OrgInfoCache.ORG_TYPE,
        )

        parser.add_argument(
            "--all-ftc-sources",
            action="store_true",
            help="Import org info from all FTC sources, instead of providing a path.",
        )

        parser.add_argument(
            "--replace",
            action="store_true",
            help="Replace/update entries when encountering previously imported org ids",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            if options.get("all_ftc_sources"):
                sources = FTC_SOURCES
            elif options.get("path"):
                sources = [(options["path"], options.get("org_type"))]
            else:
                raise CommandError("No path or sources specified, see --help")

            for path, org_type in sources:
                added = FindThatCharitySource().import_from_path(
                    path, org_type=org_type, replace=options.get("replace") or False
                )
                print("Added %s %s" % (added, org_type))
