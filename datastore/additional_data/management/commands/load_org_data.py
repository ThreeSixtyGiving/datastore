from django.core.management.base import BaseCommand
from django.db import transaction

from additional_data.models import OrgInfoCache
from additional_data.sources.find_that_charity import FindThatCharitySource


class Command(BaseCommand):
    help = "Import org info from find that charity data sources"

    def add_arguments(self, parser):

        parser.add_argument(
            type=str,
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

    def handle(self, *args, **options):

        with transaction.atomic():
            added = FindThatCharitySource().import_from_path(
                options["path"], org_type=options.get("org_type")
            )

            print("Added %s" % added)
