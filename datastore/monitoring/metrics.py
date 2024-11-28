from datetime import datetime

from django.db import transaction

from db.models import Funder, GetterRun, SourceFile, Latest
from monitoring.models import FunderMetrics, SourceFileMetrics


def gather_metrics():
    with transaction.atomic():
        timestamp = GetterRun.latest().timestamp
        gather_funders_metrics(timestamp)
        gather_sourcefiles_metrics(timestamp)


# Funder
# * "total": 21791717.610000007,
# * "grants": 4474
# * "maxAwardDate": "2023-03-30",
# *"minAwardDate": "2016-04-07


def gather_funders_metrics(timestamp):
    records = [
        funder_metrics_record(funder, timestamp) for funder in Funder.objects.all()
    ]
    FunderMetrics.objects.bulk_create(records)


def funder_metrics_record(funder: Funder, timestamp: datetime) -> FunderMetrics:
    return FunderMetrics(
        timestamp=timestamp,
        funder_org_id=funder.org_id,
        funder_non_primary_org_ids=funder.non_primary_org_ids,
        metrics=funder_metrics_values(funder),
    )


def funder_metrics_values(funder: Funder):
    return {
        "totalGBP": funder.aggregate.get("GBP", {}).get("total"),
        "grants": funder.aggregate.get("grants"),
        "maxAwardDate": funder.aggregate.get("maxAwardDate"),
        "minAwardDate": funder.aggregate.get("minAwardDate"),
    }


# SourceFile
# * lastAvailableDate: ISO timestamp


def gather_sourcefiles_metrics(timestamp: datetime):
    records = [
        sourcefile_metrics_record(sourcefile, timestamp)
        for sourcefile in Latest.objects.get(series=Latest.CURRENT).sourcefile_set
    ]
    SourceFileMetrics.objects.bulk_create(records)


def sourcefile_metrics_record(
    sourcefile: SourceFile, timestamp: datetime
) -> SourceFileMetrics:
    return SourceFileMetrics(
        timestamp=timestamp,
        publisher_prefix=sourcefile.data["publisher"]["prefix"],
        sourcefile_identifier=sourcefile.data["identifier"],
    )


def sourcefile_metrics_values(sourcefile: SourceFile):
    return {
        "lastDownloaded": sourcefile.data["datagetter_metadata"]["datetime_downloaded"],
    }
