from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError

from db.models import GetterRun, Latest


class Command(BaseCommand):
    help = "Deletes all data that has processed by the specified datagetter ids"

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
            help="Don't prompt for deletes",
        )

        parser.add_argument(
            "--oldest",
            action="store_true",
            help="Delete the oldest datagetter data",
        )

        parser.add_argument(
            "--older-than-days",
            type=int,
            help="Delete datagetter data that's more than N days old.",
        )

        parser.add_argument(
            "--update-latest-best",
            action="store_true",
            help="Update the latest best data set after deleting data",
        )

    def handle(self, *args, **options):
        if options.get("older_than_days"):
            now_dt = datetime.now()
            older_than_dt = now_dt - timedelta(days=options["older_than_days"])
            older_than_objs = (
                getter_run.pk
                for getter_run in GetterRun.objects.filter(datetime__lt=older_than_dt)
            )
            options["getter_run_ids"] = set(options["getter_run_ids"]).union(
                older_than_objs
            )

        if options.get("oldest"):
            to_delete = GetterRun.objects.order_by("datetime").first()
            options["getter_run_ids"] = set(options["getter_run_ids"]).union(
                [to_delete.pk]
            )

        if len(options["getter_run_ids"]) == 0:
            raise CommandError("No datagetter data specified")

        for run in options["getter_run_ids"]:
            try:
                confirm = "n"
                getter_run = GetterRun.objects.get(pk=run)

                if not options["no_prompt"]:
                    confirm = input("Confirm delete '%s' y/n: " % run)

                if "y" in confirm or "Y" in confirm or options["no_prompt"]:
                    getter_run.delete_all_data_from_run()
                    getter_run.delete()
                    print("Deleted %s" % run)

            except GetterRun.DoesNotExist:
                runs = [
                    str(r) for r in GetterRun.objects.all().values_list("id", flat=True)
                ]
                raise CommandError(
                    "Run id '%s' doesn't exist. Available runs %s"
                    % (run, ",".join(runs))
                )

        if options.get("update_latest_best"):
            print("Updating latest")
            Latest.update()
