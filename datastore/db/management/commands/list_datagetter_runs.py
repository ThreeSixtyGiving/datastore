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
            print("%s" % GetterRun.objects.count(), file=self.stdout)
            return

        print("id | datetime")
        for run in GetterRun.objects.all():
            print("%s | %s" % (run.pk, str(run)), file=self.stdout)
