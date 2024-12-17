from rest_framework import serializers
from rest_framework_dataclasses.serializers import DataclassSerializer

from monitoring.models import (
    PublisherMetrics,
    PublisherMetricsRecord,
    FunderMetrics,
    FunderMetricsRecord,
    SourceFileMetrics,
    SourceFileMetricsRecord,
)

# Publisher


class PublisherMetricsSerializer(DataclassSerializer):
    class Meta:
        dataclass = PublisherMetrics


class PublisherMetricsRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublisherMetricsRecord
        fields = ["timestamp", "publisher_prefix", "metrics"]

    metrics = PublisherMetricsSerializer()


# Funder


class FunderMetricsSerializer(DataclassSerializer):
    class Meta:
        dataclass = FunderMetrics


class FunderMetricsRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = FunderMetricsRecord
        fields = ["timestamp", "funder_org_id", "metrics"]

    metrics = FunderMetricsSerializer()


# SourceFile


class SourceFileMetricsSerializer(DataclassSerializer):
    class Meta:
        dataclass = SourceFileMetrics


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
