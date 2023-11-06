from django.core.management.base import BaseCommand

from additional_data.sources.nspl import NSPLSource


class Command(BaseCommand):
    help = "Imports location data from NSPL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            help="Override the URL to NSPL data.",
        )

    def handle(self, *args, **options):
        source = NSPLSource()
        source.import_nspl(options.get("url"))
