from datetime import datetime, date
from dataclasses import dataclass
from django.db import models
from django.contrib.postgres.fields import ArrayField


@dataclass
class PublisherMetrics:
    total_grants: int
    total_gbp: float
    total_funders: int
    total_recipient_individuals: int
    total_recipient_organisations: int


class PublisherMetricsRecord(models.Model):
    timestamp = models.DateTimeField()
    publisher_prefix = models.TextField()
    metrics = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"<PublisherMetrics {self.timestamp} {self.publisher_prefix}>"


@dataclass
class FunderMetrics:
    total_grants: int
    total_gbp: float
    latest_award_date: date
    earliest_award_date: date


class FunderMetricsRecord(models.Model):
    timestamp = models.DateTimeField()
    funder_org_id = models.TextField()
    funder_non_primary_org_ids = ArrayField(models.TextField())
    metrics = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"<FunderMetrics {self.timestamp} {self.funder_org_id} {self.funder_non_primary_org_ids}>"


@dataclass
class SourceFileMetrics:
    last_downloaded_at: datetime
    valid: bool


class SourceFileMetricsRecord(models.Model):
    timestamp = models.DateTimeField()
    publisher_prefix = models.TextField()
    sourcefile_identifier = models.TextField()
    sourcefile_url = models.TextField()
    metrics = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"<SourceFileMetrics {self.timestamp} {self.publisher_prefix} {self.sourcefile_identifier}>"
