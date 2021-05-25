from django.core.management.base import BaseCommand, CommandError

from db.models import GetterRun


class Command(BaseCommand):
    help = "Archive the getter run by the specified getter run ids. Archiving deletes grant data but not the metadata (SourceFiles, Publishers)"

    def add_arguments(self, parser):
        parser.add_argument(
            type=int,
            nargs="*",
            action="store",
            dest="getter_run_ids",
            help="The datagetter run ids",
        )

        parser.add_argument(
            "--no-prompt",
            action="store_true",
            help="Don't prompt for archiving",
        )

        parser.add_argument(
            "--oldest",
            action="store_true",
            help="Archives the oldest getter run",
        )

    def handle(self, *args, **options):
        if options.get("oldest"):
            to_delete = GetterRun.objects.order_by("datetime").first()
            options["getter_run_ids"] = [to_delete.pk]

        if len(options["getter_run_ids"]) == 0:
            raise CommandError("No datagetter data specified")

        for run in options["getter_run_ids"]:
            try:
                confirm = "n"
                getter_run = GetterRun.objects.get(pk=run)

                if not options["no_prompt"]:
                    confirm = input("Confirm delete grant data '%s' y/n: " % run)

                if "y" in confirm or "Y" in confirm or options["no_prompt"]:
                    getter_run.archive_run()
                    print("Archived %s" % run)

            except GetterRun.DoesNotExist:
                raise CommandError("Run id '%s' doesn't exist " % run)
