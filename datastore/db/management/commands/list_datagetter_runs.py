from django.core.management.base import BaseCommand

from db.models import GetterRun


class Command(BaseCommand):
    help = "Lists all datagetter ids"

    def add_arguments(self, parser):
        parser.add_argument(
            "--total",
            action="store_true",
            help="Just output the total datagetter runs in the db",
        )

    def handle(self, *args, **options):
        if options.get("total"):
            self.stdout.write("%s" % GetterRun.objects.count())
            return

        self.stdout.write("id  | datetime                         | in_use")
        for run in GetterRun.objects.all():
            self.stdout.write(
                "{:<3} | {} | {}".format(run.pk, run.datetime, run.is_in_use())
            )
