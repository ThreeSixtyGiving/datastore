from django.core.management.base import BaseCommand

from additional_data.sources.nspl import NSPLSource


class Command(BaseCommand):
    help = "Imports location data from NSPL"

    def handle(self, *args, **options):
        source = NSPLSource()
        source.import_nspl()
