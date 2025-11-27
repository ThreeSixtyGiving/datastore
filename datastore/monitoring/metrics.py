import logging
from datetime import datetime, timedelta
from typing import Optional, List

from django.db import transaction
from django.db.models import FloatField, BigIntegerField
from django.db.models.aggregates import Sum, Count
from django.db.models.fields import TextField
from django.db.models.functions import Cast

from db.models import Funder, GetterRun, SourceFile, Publisher, Latest, Recipient
from monitoring.models import (
    FUZZY_DAY_LEEWAY_HOURS,
    PublisherMetricsRecord,
    FunderMetricsRecord,
    SourceFileMetricsRecord,
    PublisherMetrics,
    FunderMetrics,
    SourceFileMetrics,
    MonitoringSnapshot,
    DatasetMetrics,
    DatasetMetricsRecord,
)
from monitoring.serializers import (
    PublisherMetricsSerializer,
    FunderMetricsSerializer,
    SourceFileMetricsSerializer,
    DatasetMetricsSerializer,
)

logger = logging.getLogger(__name__)


def gather_metrics(timestamp: Optional[datetime] = None) -> None:
    with transaction.atomic():
        if not timestamp:
            timestamp = GetterRun.latest().datetime

        snapshot = MonitoringSnapshot.objects.create(
            timestamp=timestamp, latest_getter_run_id=GetterRun.latest().id
        )

        created_dataset_record = gather_dataset_metrics(snapshot)
        logger.info(f"Created dataset record {created_dataset_record}")

        created_publisher_metrics = gather_publisher_metrics(snapshot)
        logger.info(
            "Created %s publisher metrics records", len(created_publisher_metrics)
        )

        created_funder_metrics = gather_funders_metrics(snapshot)
        logger.info("Created %s funder metrics records", len(created_funder_metrics))

        created_source_file_metrics = gather_source_files_metrics(snapshot)
        logger.info(
            "Created %s source file metrics records", len(created_source_file_metrics)
        )

        logger.info(
            f"Created Snapshot {snapshot.id} @ {snapshot.timestamp.isoformat()}"
        )


# Dataset


def dataset_metrics(latest: Latest) -> DatasetMetrics:
    # The Latest Best dataset comprises a set of sourcefiles
    sourcefiles = latest.sourcefile_set
    grants = latest.grant_set

    sf_agg = sourcefiles.aggregate(
        # In postgresql JSONB values must be cast before aggregate functions
        total_grants=Sum(Cast("aggregate__count", BigIntegerField())),
        total_gbp=Sum(Cast("aggregate__currencies__GBP__total_amount", FloatField())),
    )

    gr_agg = grants.aggregate(
        total_grants_to_individuals=Count(
            Cast("data__recipientIndividual__id", TextField()), distinct=False
        ),
        total_recipient_individuals=Count(
            Cast("data__recipientIndividual__id", TextField()), distinct=True
        ),
    )

    return DatasetMetrics(
        total_grants=sf_agg["total_grants"],
        total_grants_to_individuals=gr_agg["total_grants_to_individuals"],
        total_amount_awarded_gbp=sf_agg["total_gbp"],
        total_publishers=Publisher.objects.all().count(),
        total_funders=Funder.objects.count(),
        total_recipient_organisations=Recipient.objects.count(),
        total_recipient_individuals=gr_agg["total_recipient_individuals"],
    )


def gather_dataset_metrics(
    snapshot: MonitoringSnapshot,
) -> Optional[DatasetMetricsRecord]:
    try:
        record = DatasetMetricsRecord.objects.create(
            snapshot=snapshot,
            timestamp=snapshot.timestamp,
            metrics=DatasetMetricsSerializer(
                dataset_metrics(Latest.objects.get(series=Latest.CURRENT))
            ).data,
        )
        return record
    except Exception as e:
        logger.error("Failed to create metrics record for Dataset: %s", e)


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


def gather_publisher_metrics(
    snapshot: MonitoringSnapshot,
) -> List[PublisherMetricsRecord]:
    records = list()
    for publisher in Publisher.objects.order_by().all():
        try:
            records.append(
                PublisherMetricsRecord(
                    snapshot=snapshot,
                    timestamp=snapshot.timestamp,
                    publisher_prefix=publisher.prefix,
                    metrics=PublisherMetricsSerializer(
                        publisher_metrics(publisher)
                    ).data,
                )
            )
        except Exception as e:
            logger.error(
                "Exception while creating metrics record for Publisher %s: %s",
                publisher.name,
                e,
            )
    return PublisherMetricsRecord.objects.bulk_create(records)


# Funder


def funder_metrics(funder: Funder) -> FunderMetrics:

    total_gbp = 0
    try:
        total_gbp += funder.aggregate["currencies"]["GBP"]["recipient_org"]["total"]
    except KeyError:
        pass

    try:
        total_gbp += funder.aggregate["currencies"]["GBP"]["recipient_ind"]["total"]
    except KeyError:
        pass

    return FunderMetrics(
        total_grants=funder.aggregate.get("grants"),
        total_gbp=total_gbp,
        latest_award_date=funder.aggregate.get("maxAwardDate"),
        earliest_award_date=funder.aggregate.get("minAwardDate"),
    )


def gather_funders_metrics(snapshot: MonitoringSnapshot) -> List[FunderMetricsRecord]:
    records = list()
    for funder in Funder.objects.all():
        try:
            records.append(
                FunderMetricsRecord(
                    snapshot=snapshot,
                    timestamp=snapshot.timestamp,
                    funder_org_id=funder.org_id,
                    funder_non_primary_org_ids=funder.non_primary_org_ids,
                    metrics=FunderMetricsSerializer(funder_metrics(funder)).data,
                )
            )
        except Exception as e:
            logger.error(
                "Exception while creating metrics record for Funder %s: %s",
                funder.org_id,
                e,
            )
    return FunderMetricsRecord.objects.bulk_create(records)


# SourceFile


def source_file_metrics(sourcefile: SourceFile) -> SourceFileMetrics:
    # Note that "best" refers to the last successful download attempt
    best_metadata = sourcefile.data["datagetter_metadata"]
    last_attempt = GetterRun.latest().sourcefile_set.get(
        data__identifier=sourcefile.data["identifier"]
    )
    last_attempt_metadata = last_attempt.data["datagetter_metadata"]

    # datetime downloaded is in format "2025-01-27T00:02:46+00:00"
    best_downloaded_datetime = datetime.fromisoformat(
        best_metadata["datetime_downloaded"]
    )
    last_attempt_downloaded_datetime = datetime.fromisoformat(
        last_attempt_metadata["datetime_downloaded"]
    )

    days_since_last_successful_download = (
        last_attempt_downloaded_datetime - best_downloaded_datetime
    ).days

    # Allow a few hours leeway to create a more human definition of "days", e.g. more than 20 hours
    # ago counts as being "one day" ago
    # Implemented as: "Would a new day be counted within the next 4 hours?" => count a day now
    if (
        (last_attempt_downloaded_datetime - best_downloaded_datetime)
        + timedelta(hours=FUZZY_DAY_LEEWAY_HOURS)
    ).days > days_since_last_successful_download:
        days_since_last_successful_download += 1

    return SourceFileMetrics(
        last_successful_download_at=best_downloaded_datetime,
        last_download_attempt_at=last_attempt_downloaded_datetime,
        last_download_attempt_download_url=last_attempt.data["distribution"][0][
            "downloadURL"
        ],
        last_download_attempt_downloaded=last_attempt_metadata["downloads"],
        last_download_attempt_valid=last_attempt_metadata.get("valid"),
        last_download_attempt_error=last_attempt_metadata.get("error", ""),
        days_since_last_successful_download=days_since_last_successful_download,
        last_download_attempt_access_url=last_attempt.data["distribution"][0].get(
            "accessURL"
        ),
        last_successful_download_was_at_least_7_days_ago=bool(
            days_since_last_successful_download >= 7
        ),
    )


def gather_source_files_metrics(snapshot: MonitoringSnapshot):
    records = list()
    for sourcefile in Latest.objects.get(series=Latest.CURRENT).sourcefile_set.all():
        sourcefile: SourceFile
        try:
            records.append(
                SourceFileMetricsRecord(
                    snapshot=snapshot,
                    timestamp=snapshot.timestamp,
                    publisher_prefix=sourcefile.data["publisher"]["prefix"],
                    sourcefile_identifier=sourcefile.data["identifier"],
                    sourcefile_url=sourcefile.data["distribution"][0]["downloadURL"],
                    metrics=SourceFileMetricsSerializer(
                        source_file_metrics(sourcefile)
                    ).data,
                )
            )
        except Exception as e:
            logger.error(
                "Exception while creating metrics record for SourceFile %s: %s",
                sourcefile.data.get("identifier"),
                e,
            )
    return SourceFileMetricsRecord.objects.bulk_create(records)
