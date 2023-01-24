from django.core.management.base import BaseCommand

from additional_data.sources.codelist_code import CodeListSource


class Command(BaseCommand):
    help = "Imports 360Giving standard codelist data"

    def handle(self, *args, **options):
        source = CodeListSource()
        source.import_codelists()
