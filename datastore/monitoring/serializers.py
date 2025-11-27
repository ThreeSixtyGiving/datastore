import csv
import io
from typing import Iterable
from datetime import datetime
from typing import Dict, Any

from django.db.models import QuerySet
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework_dataclasses.serializers import DataclassSerializer

from monitoring.models import (
    DatasetMetrics,
    DatasetMetricsRecord,
    PublisherMetrics,
    PublisherMetricsRecord,
    FunderMetrics,
    FunderMetricsRecord,
    SourceFileMetrics,
    SourceFileMetricsRecord,
    ChangedRecord,
)


class DateTimeFieldSerialiser(serializers.DateTimeField):
    def to_representation(self, value: datetime):
        return value.isoformat()


class BaseMetricsSerializer(DataclassSerializer):
    def to_internal_value(self, data: Dict[str, Any]):
        """The parent MetricsRecord needs a JSON-like value."""
        dataclass_value = super().to_internal_value(data)
        # re-serialise the dataclass back again
        json_value = self.__class__(dataclass_value)
        return json_value.data


# Dataset


class DatasetMetricsSerializer(BaseMetricsSerializer):
    class Meta:
        dataclass = DatasetMetrics


class DatasetMetricsRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetMetricsRecord
        fields = ["timestamp", "metrics"]

    metrics = DatasetMetricsSerializer()


# SourceFile


class SourceFileMetricsSerializer(BaseMetricsSerializer):
    class Meta:
        dataclass = SourceFileMetrics

    last_download_attempt_error = serializers.CharField(
        allow_blank=True, allow_null=True
    )


class SourceFileMetricsRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceFileMetricsRecord
        fields = [
            "timestamp",
            "publisher_prefix",
            "sourcefile_identifier",
            "sourcefile_url",
            "metrics",
        ]

    metrics = SourceFileMetricsSerializer()


# Publisher


class PublisherMetricsSerializer(BaseMetricsSerializer):
    class Meta:
        dataclass = PublisherMetrics


class PublisherMetricsRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublisherMetricsRecord
        fields = ["timestamp", "publisher_prefix", "metrics"]

    metrics = PublisherMetricsSerializer()


class PublisherMetricsRecordWithDownSourceFilesSerializer(serializers.ModelSerializer):
    """
    Include info about down source files with each publisher.
    """

    class Meta:
        model = PublisherMetricsRecord
        fields = [
            "timestamp",
            "publisher_prefix",
            "metrics",
            "down_source_files",
            "has_sourcefile_where_last_successful_download_was_at_least_7_days_ago",
        ]

    metrics = PublisherMetricsSerializer()
    down_source_files = SerializerMethodField(method_name="get_down_source_files_json")
    has_sourcefile_where_last_successful_download_was_at_least_7_days_ago = (
        SerializerMethodField()
    )

    @classmethod
    def _get_down_source_files(
        self, obj: PublisherMetricsRecord
    ) -> QuerySet[SourceFileMetricsRecord]:
        return obj.snapshot.sourcefilemetricsrecord_set.filter(
            publisher_prefix=obj.publisher_prefix,
            metrics__days_since_last_successful_download__gt=0,
        )

    @classmethod
    def get_down_source_files_json(cls, obj: PublisherMetricsRecord):
        return SourceFileMetricsRecordSerializer(
            cls._get_down_source_files(obj), many=True
        ).data

    @classmethod
    def get_has_sourcefile_where_last_successful_download_was_at_least_7_days_ago(
        cls, obj: PublisherMetricsRecord
    ) -> bool:
        for sf in cls._get_down_source_files(obj):
            if sf.metrics.get("days_since_last_successful_download", 0) >= 7:
                return True
        return False


def list_to_csv(data: Iterable) -> str:
    """Render a list as a single row of quoted CSV"""
    f = io.StringIO()
    writer = csv.writer(f, quoting=csv.QUOTE_ALL)
    writer.writerow(data)
    return f.getvalue().strip()


class PublisherMetricsRecordWithDownSourceFilesSerializerCSV(
    PublisherMetricsRecordWithDownSourceFilesSerializer,
):
    SOURCE_FILE_NESTED_CSV_FIELDS = [
        "last_successful_download_at",
        "last_download_attempt_at",
        "last_download_attempt_download_url",
        "last_download_attempt_downloaded",
        "last_download_attempt_valid",
        "last_download_attempt_error",
        "days_since_last_successful_download",
        "last_download_attempt_access_url",
        "last_successful_download_was_at_least_7_days_ago",
    ]

    down_source_files = SerializerMethodField(method_name="get_down_source_files_csv")

    @classmethod
    def get_down_source_files_csv(cls, obj: PublisherMetricsRecord):
        down_source_files_records = cls._get_down_source_files(obj)

        # Nested CSV in a CSV field isn't very nice, but it works for the SalesForce integration
        data = {
            metric_name: list_to_csv(
                down_source_files_records.values_list(
                    f"metrics__{metric_name}", flat=True
                )
            )
            for metric_name in cls.SOURCE_FILE_NESTED_CSV_FIELDS
        }

        return data


# Funder


class FunderMetricsSerializer(BaseMetricsSerializer):
    class Meta:
        dataclass = FunderMetrics


class FunderMetricsRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = FunderMetricsRecord
        fields = ["timestamp", "funder_org_id", "funder_non_primary_org_ids", "metrics"]

    metrics = FunderMetricsSerializer()


class ChangedFunderMetricsRecordJSONSerializer(DataclassSerializer):
    class Meta:
        dataclass = ChangedRecord

    start_record = FunderMetricsRecordSerializer()
    end_record = FunderMetricsRecordSerializer()


class ChangedFunderMetricsRecordCSVSerializer(ChangedFunderMetricsRecordJSONSerializer):
    NESTED_CSV_FIELDS = [
        "changed_metrics",
    ]

    def to_representation(self, changed_record: ChangedRecord):
        data = super().to_representation(changed_record)

        # Nested CSV in a CSV field isn't very nice, but it works for the SalesForce integration
        for field_name in self.NESTED_CSV_FIELDS:
            data[field_name] = list_to_csv(data[field_name])

        return data
