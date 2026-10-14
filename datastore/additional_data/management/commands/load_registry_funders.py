from django.core.management.base import BaseCommand

from additional_data.sources.registry_funders import RegistryFundersSource


class Command(BaseCommand):
    help = "Imports funder data from the registry"

    def handle(self, *args, **options):
        source = RegistryFundersSource()
        source.import_registry_funders()
