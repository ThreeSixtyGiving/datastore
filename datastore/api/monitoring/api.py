from typing import Type
from datetime import datetime, date

from django.utils import timezone
from rest_framework.generics import ListAPIView
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
)


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


class FunderMetricsSnapshotAPIView(SnapshotAPIView):
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)
    serializer_class = FunderMetricsRecordSerializer

    metrics_record_model = FunderMetricsRecord


class SourceFileMetricsSnapshotAPIView(SnapshotAPIView):
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)
    serializer_class = SourceFileMetricsRecordSerializer

    metrics_record_model = SourceFileMetricsRecord
