import logging
from typing import Type, cast
from datetime import datetime, date

from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.settings import api_settings
from rest_framework_csv.renderers import CSVRenderer

from monitoring.models import (
    DatasetMetricsRecord,
    PublisherMetricsRecord,
    FunderMetricsRecord,
    SourceFileMetricsRecord,
    AbstractMetricsRecord,
)
from monitoring.serializers import (
    DatasetMetricsRecordSerializer,
    PublisherMetricsRecordSerializer,
    FunderMetricsRecordSerializer,
    SourceFileMetricsRecordSerializer,
    PublisherMetricsRecordWithDownSourceFilesSerializer,
    PublisherMetricsRecordWithDownSourceFilesSerializerCSV,
    ChangedFunderMetricsRecordJSONSerializer,
    ChangedFunderMetricsRecordCSVSerializer,
)

logger = logging.getLogger(__name__)


class SnapshotAPIView(ListAPIView):
    """
    View containing shared logic to lookup snapshots of a timeseries table
    based on the `timestamp` model field and specified identifier fields.
    """

    metrics_record_model: Type[AbstractMetricsRecord]

    def get_queryset(self):
        snapshot_date_str = self.kwargs.get("snapshot_date")

        if snapshot_date_str is None:
            # default to today's latest snapshot
            snapshot_date = timezone.now().date()
        else:
            # convert from str to date
            snapshot_date = date.fromisoformat(snapshot_date_str)

        # Find the latest snapshot on the given day, or earlier
        # (before the end of day based on configured timezone/calendar)
        snapshot_date_end_of_day = datetime.combine(
            snapshot_date, datetime.max.time(), tzinfo=timezone.get_current_timezone()
        )

        return self.metrics_record_model.get_records_at(at=snapshot_date_end_of_day)


class DatasetMetricsSnapshotAPIView(SnapshotAPIView):
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)
    serializer_class = DatasetMetricsRecordSerializer

    metrics_record_model = DatasetMetricsRecord


class PublisherMetricsSnapshotAPIView(SnapshotAPIView):
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)
    serializer_class = PublisherMetricsRecordSerializer

    metrics_record_model = PublisherMetricsRecord


class PublisherSourceFileDownAPIView(SnapshotAPIView):
    """
    This view lists only Publishers that have an unavailable source file,
    and info relevant to the down Source files.
    """

    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)

    metrics_record_model = PublisherMetricsRecord

    def get_serializer_class(self):
        request: Request = cast(Request, self.request)
        if request.accepted_renderer.format == "csv":
            return PublisherMetricsRecordWithDownSourceFilesSerializerCSV
        else:
            return PublisherMetricsRecordWithDownSourceFilesSerializer

    def get_queryset(self):
        publisher_records = super().get_queryset()
        down_publisher_prefixes = set()

        # Theoretically this could be a single SQL query instead of a loop,
        # but I couldn't get the obvious ways to work.
        # This is NOT a performance critical area.
        for pub in publisher_records.prefetch_related(
            "snapshot__sourcefilemetricsrecord_set"
        ):
            if (
                pub.snapshot.sourcefilemetricsrecord_set.filter(
                    publisher_prefix=pub.publisher_prefix,
                    metrics__days_since_last_successful_download__gte=1,
                ).count()
                > 0
            ):
                down_publisher_prefixes.add(pub.publisher_prefix)
                logger.info(
                    "Down publisher prefix: %s",
                    pub.publisher_prefix,
                )

        return publisher_records.filter(publisher_prefix__in=down_publisher_prefixes)


class FunderMetricsSnapshotAPIView(SnapshotAPIView):
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)
    serializer_class = FunderMetricsRecordSerializer

    metrics_record_model = FunderMetricsRecord


class SourceFileMetricsSnapshotAPIView(SnapshotAPIView):
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)
    serializer_class = SourceFileMetricsRecordSerializer

    metrics_record_model = SourceFileMetricsRecord


class ChangedFunderMetricsRecordAPIView(ListAPIView):
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)

    def get_serializer_class(self):
        request: Request = cast(Request, self.request)
        if request.accepted_renderer.format == "csv":
            return ChangedFunderMetricsRecordCSVSerializer
        else:
            return ChangedFunderMetricsRecordJSONSerializer

    def get_queryset(self):
        start_date = date.fromisoformat(self.kwargs.get("start_date"))
        end_date = date.fromisoformat(self.kwargs.get("end_date"))

        start_dt = datetime.combine(
            start_date, datetime.max.time(), tzinfo=timezone.get_current_timezone()
        )
        end_dt = datetime.combine(
            end_date,
            datetime.max.time(),
            tzinfo=timezone.get_current_timezone(),
        )

        records = FunderMetricsRecord.get_records_with_changes_between(start_dt, end_dt)
        return records
