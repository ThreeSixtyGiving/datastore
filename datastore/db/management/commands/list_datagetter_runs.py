from django.core.management.base import BaseCommand

from db.models import GetterRun


class Command(BaseCommand):
    help = "Lists all datagetter ids"

    def handle(self, *args, **options):
        print("id | datetime")
        for run in GetterRun.objects.all():
            print("%s | %s" % (run.pk, str(run)))
