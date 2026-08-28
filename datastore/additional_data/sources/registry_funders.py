import logging

import requests
from django.conf import settings
from django.db import transaction

from additional_data.models import RegistryFunder

logger = logging.getLogger(__name__)


class RegistryFundersSource(object):
    """Imports funder records from the registry"""

    ADDITIONAL_DATA_KEY = "registryFunder"

    def import_registry_funders(self) -> int:
        url = settings.REGISTRY_FUNDERS_URL
        logger.info(f"Fetching registry funders from {url}")

        r = requests.get(url)
        r.raise_for_status()
        records = r.json()

        funders = [
            RegistryFunder(
                salesforce_id=salesforce_id,
                org_id=record.get("orgIdentifier") or None,
                data=record,
            )
            for salesforce_id, record in records.items()
        ]

        with transaction.atomic():
            RegistryFunder.objects.all().delete()
            RegistryFunder.objects.bulk_create(funders)

        funder_count = len(funders)
        logger.info(f"Loaded {funder_count} funders from the registry")
        return funder_count

    def update_additional_data(self, grant, source_file, additional_data):
        try:
            funding_org_id = grant["fundingOrganization"][0]["id"]
        except (KeyError, IndexError, TypeError):
            return

        registry_funder = RegistryFunder.objects.filter(org_id=funding_org_id).first()
        if registry_funder:
            additional_data[self.ADDITIONAL_DATA_KEY] = registry_funder.data
