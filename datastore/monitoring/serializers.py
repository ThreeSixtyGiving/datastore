from datetime import datetime
from typing import Dict, Any

from rest_framework import serializers
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


# Publisher


class PublisherMetricsSerializer(BaseMetricsSerializer):
    class Meta:
        dataclass = PublisherMetrics


class PublisherMetricsRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublisherMetricsRecord
        fields = ["timestamp", "publisher_prefix", "metrics"]

    metrics = PublisherMetricsSerializer()


# Funder


class FunderMetricsSerializer(BaseMetricsSerializer):
    class Meta:
        dataclass = FunderMetrics


class FunderMetricsRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = FunderMetricsRecord
        fields = ["timestamp", "funder_org_id", "funder_non_primary_org_ids", "metrics"]

    metrics = FunderMetricsSerializer()


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
