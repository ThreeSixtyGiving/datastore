import logging
from datetime import datetime

from django.db import transaction

from db.models import Funder, GetterRun, SourceFile, Publisher, Latest
from monitoring.models import (
    PublisherMetricsRecord,
    FunderMetricsRecord,
    SourceFileMetricsRecord,
    PublisherMetrics,
    FunderMetrics,
    SourceFileMetrics,
)
from monitoring.serializers import (
    PublisherMetricsSerializer,
    FunderMetricsSerializer,
    SourceFileMetricsSerializer,
)

logger = logging.getLogger(__name__)


def gather_metrics():
    with transaction.atomic():
        timestamp = GetterRun.latest().datetime

        created_publisher_metrics = gather_publisher_metrics(timestamp)
        logger.info(
            "Created %s publisher metrics records", len(created_publisher_metrics)
        )

        created_funder_metrics = gather_funders_metrics(timestamp)
        logger.info("Created %s funder metrics records", len(created_funder_metrics))

        created_source_file_metrics = gather_source_files_metrics(timestamp)
        logger.info(
            "Created %s source file metrics records", len(created_source_file_metrics)
        )


# Publisher


def publisher_metrics(publisher: Publisher) -> PublisherMetrics:
    return PublisherMetrics(
        total_grants=publisher.aggregate["total"].get("grants", None),
        total_gbp=publisher.aggregate["total"].get("GBP", None),
        total_funders=publisher.aggregate["total"].get("funders", None),
        total_recipient_individuals=publisher.aggregate["total"].get(
            "recipientIndividuals", None
        ),
        total_recipient_organisations=publisher.aggregate["total"].get(
            "recipientOrganisations", None
        ),
    )


def gather_publisher_metrics(timestamp: datetime):
    records = [
        PublisherMetricsRecord(
            timestamp=timestamp,
            publisher_prefix=publisher.prefix,
            metrics=PublisherMetricsSerializer(publisher_metrics(publisher)).data,
        )
        for publisher in Publisher.objects.filter(getter_run=GetterRun.latest())
    ]
    return PublisherMetricsRecord.objects.bulk_create(records)


# Funder


def funder_metrics(funder: Funder) -> FunderMetrics:
    return FunderMetrics(
        total_grants=funder.aggregate.get("grants"),
        total_gbp=funder.aggregate["currencies"].get("GBP", {}).get("total"),
        latest_award_date=funder.aggregate.get("maxAwardDate"),
        earliest_award_date=funder.aggregate.get("minAwardDate"),
    )


def gather_funders_metrics(timestamp):
    records = [
        FunderMetricsRecord(
            timestamp=timestamp,
            funder_org_id=funder.org_id,
            funder_non_primary_org_ids=funder.non_primary_org_ids,
            metrics=FunderMetricsSerializer(funder_metrics(funder)).data,
        )
        for funder in Funder.objects.all()
    ]
    return FunderMetricsRecord.objects.bulk_create(records)


# SourceFile


def source_file_metrics(sourcefile: SourceFile) -> SourceFileMetrics:
    datagetter_metadata = sourcefile.data["datagetter_metadata"]
    return SourceFileMetrics(
        last_downloaded_at=datagetter_metadata["datetime_downloaded"],
        valid=datagetter_metadata["valid"],
    )


def gather_source_files_metrics(timestamp: datetime):
    records = [
        SourceFileMetricsRecord(
            timestamp=timestamp,
            publisher_prefix=sourcefile.data["publisher"]["prefix"],
            sourcefile_identifier=sourcefile.data["identifier"],
            sourcefile_url=sourcefile.data["distribution"][0]["downloadURL"],
            metrics=SourceFileMetricsSerializer(source_file_metrics(sourcefile)).data,
        )
        for sourcefile in Latest.objects.get(series=Latest.CURRENT).sourcefile_set.all()
    ]
    return SourceFileMetricsRecord.objects.bulk_create(records)
