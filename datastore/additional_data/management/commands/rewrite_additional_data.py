import logging

from django.core.management.base import BaseCommand
from django.core.paginator import Paginator

from additional_data.generator import AdditionalDataGenerator, DATA_SOURCES
from db.models import Grant, Latest

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 10_000


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
            "--grants-chunk-size",
            type=int,
            action="store",
            default=DEFAULT_CHUNK_SIZE,
            help="Number of Grants to update simultaneously",
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
        data_sources = options["data_sources"]
        chunk_size = options.get("grants_chunk_size")
        paginator = Paginator(grants.order_by("grant_id"), chunk_size)

        # Update Grants in a separate function so the memory can be reclaimed between chunks
        def update_grants_page(page_num):
            page = paginator.page(page_num)
            page_grants = page.object_list

            logger.info(
                f"Updating Grants {page.start_index()}-{page.end_index()} of {paginator.count}"
            )

            for grant in page_grants:
                if data_sources:
                    additional_data = generator.create(grant.data, data_sources)
                else:
                    additional_data = generator.create(grant.data)

                grant.additional_data = additional_data

            Grant.objects.bulk_update(page_grants, ["additional_data"])

        for page_num in paginator.page_range:
            update_grants_page(page_num)

        logger.info(f"Updated {paginator.count} Grants Additional Data")
