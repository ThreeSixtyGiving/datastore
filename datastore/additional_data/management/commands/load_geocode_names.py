from django.core.management.base import BaseCommand

from additional_data.sources.code_names import GeoCodeNamesSource


class Command(BaseCommand):
    help = "Imports location code names"

    def handle(self, *args, **options):
        source = GeoCodeNamesSource()
        source.import_code_names()
