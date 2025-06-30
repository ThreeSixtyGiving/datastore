import csv
import io
from typing import Iterable
from datetime import datetime
from typing import Dict, Any

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
        fields = ["timestamp", "publisher_prefix", "metrics", "down_source_files"]

    metrics = PublisherMetricsSerializer()
    down_source_files = SerializerMethodField(method_name="get_down_source_files_json")

    @staticmethod
    def get_down_source_files_json(obj: PublisherMetricsRecord):
        down_source_files_records = obj.snapshot.sourcefilemetricsrecord_set.filter(
            publisher_prefix=obj.publisher_prefix,
            metrics__last_successful_download_was_at_least_7_days_ago=True,
        )
        return SourceFileMetricsRecordSerializer(
            down_source_files_records, many=True
        ).data


def list_to_csv(data: Iterable) -> str:
    """Render a list as a single row of quoted CSV"""
    f = io.StringIO()
    writer = csv.writer(f, quoting=csv.QUOTE_ALL)
    writer.writerow(data)
    return f.getvalue()


class PublisherMetricsRecordWithDownSourceFilesSerializerCSV(
    PublisherMetricsRecordWithDownSourceFilesSerializer,
):
    down_source_files = SerializerMethodField(method_name="get_down_source_files_csv")

    @staticmethod
    def get_down_source_files_csv(obj: PublisherMetricsRecord):
        down_source_files_records = obj.snapshot.sourcefilemetricsrecord_set.filter(
            publisher_prefix=obj.publisher_prefix,
            metrics__last_successful_download_was_at_least_7_days_ago=True,
        )

        # Nested CSV in a CSV field isn't very nice, but it works for the SalesForce integration
        data = {
            "last_download_attempt_download_url": list_to_csv(
                down_source_files_records.values_list(
                    "metrics__last_download_attempt_download_url", flat=True
                )
            ),
            "last_download_attempt_access_url": list_to_csv(
                down_source_files_records.values_list(
                    "metrics__last_download_attempt_access_url", flat=True
                )
            ),
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
