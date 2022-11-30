from django.core.management.base import BaseCommand

from additional_data.generator import AdditionalDataGenerator
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

    def handle(self, *args, **options):

        if "latest" in options["getter_run"]:
            grants = Latest.objects.get(series=Latest.CURRENT).grant_set.all()
        else:
            grants = Grant.objects.filter(getter_run=options["getter_run"])

        generator = AdditionalDataGenerator()

        for grant in grants:
            additional_data = generator.create(grant.data)
            grant.additional_data = additional_data

        Grant.objects.bulk_update(grants, ["additional_data"], batch_size=10000)
