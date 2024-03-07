from django.core.management.base import BaseCommand

from additional_data.generator import AdditionalDataGenerator, DATA_SOURCES
from db.models import Grant, Latest


class Command(BaseCommand):
    help = (
        "Reloads the additional data on grant data specified by datagetter id or latest"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            type=str,
            action="store",
            dest="getter_run",
            help="The datagetter run id or latest",
        )

        parser.add_argument(
            "--data-sources",
            type=str,
            action="store",
            dest="data_sources",
            nargs="*",
            default=None,
            help=f"Customise the data sources to used to update additional_data. Available sources: {DATA_SOURCES}",
        )

    def handle(self, *args, **options):

        if "latest" in options["getter_run"]:
            grants = Latest.objects.get(series=Latest.CURRENT).grant_set.all()
        else:
            grants = Grant.objects.filter(getter_run=options["getter_run"])

        generator = AdditionalDataGenerator()

        for grant in grants:
            if options["data_sources"]:
                additional_data = generator.create(grant.data, options["data_sources"])
            else:
                additional_data = generator.create(grant.data)

            grant.additional_data = additional_data

        Grant.objects.bulk_update(grants, ["additional_data"], batch_size=10000)
