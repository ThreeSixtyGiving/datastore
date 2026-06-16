from datetime import datetime, timezone

from django.core.management.base import BaseCommand, CommandError

from db.models import Status, Statuses
from prometheus.views import (
    DURATION_OF_LAST_RUN_FOR_DATAGETTER,
    DURATION_OF_LAST_RUN_FOR_DATASTORE_LOAD,
    DURATION_OF_LAST_RUN_FOR_GRANTNAV_DATA_PACKAGE_BUILD,
    DURATION_OF_LAST_RUN_FOR_MONITORING_SNAPSHOT,
)


class Command(BaseCommand):
    help = "Sets a status flag"

    def add_arguments(self, parser):
        parser.add_argument(
            "--list-options",
            action="store_true",
            help="List the status and items to be in a status",
        )

        parser.add_argument(
            "--list",
            action="store_true",
            help="List the status and items to be in a status",
        )

        parser.add_argument(
            "--what",
            action="store",
            dest="what",
            help="The thing to set the status of e.g. datagetter",
        )

        parser.add_argument(
            "--status",
            action="store",
            dest="status",
            help="The status to set the thing to e.g. IN_PROGRESS",
        )

    def handle(self, *args, **options):

        if options.get("list_options"):
            # TODO future refactor as this is a bit clunky
            print(Statuses.__dict__)
            return

        if options.get("list"):
            print(Status.objects.all().values())
            return

        if options.get("status") and options.get("what"):
            item, c = Status.objects.get_or_create(what=options["what"])
            try:
                item.status = Statuses.__dict__.get(options["status"])
            except KeyError:
                CommandError("Unknown status use --list-options to list statuses")

            if Statuses.__dict__.get(options["status"]) in (
                Statuses.IDLE,
                Statuses.READY,
            ):
                if options.get("what") == "datagetter":
                    DURATION_OF_LAST_RUN_FOR_DATAGETTER.set(
                        (datetime.now(timezone.utc) - item.when).total_seconds()
                    )

                elif options.get("what") == "datastore":
                    DURATION_OF_LAST_RUN_FOR_DATASTORE_LOAD.set(
                        (datetime.now(timezone.utc) - item.when).total_seconds()
                    )

                elif options.get("what") == "grantnav_data_package":
                    DURATION_OF_LAST_RUN_FOR_GRANTNAV_DATA_PACKAGE_BUILD.set(
                        (datetime.now(timezone.utc) - item.when).total_seconds()
                    )

                elif options.get("what") == "monitoring_snapshot":
                    DURATION_OF_LAST_RUN_FOR_MONITORING_SNAPSHOT.set(
                        (datetime.now(timezone.utc) - item.when).total_seconds()
                    )

            item.save()
        else:
            raise CommandError("Not enough parameters supplied to set status")
