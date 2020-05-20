from django.core.management.base import BaseCommand

from additional_data.sources.geo_lookup import GeoLookupSource


class Command(BaseCommand):
    help = "Imports location data from drkane/geo-lookups"

    def handle(self, *args, **options):
        source = GeoLookupSource()
        source.import_geo_lookups()
