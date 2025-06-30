from typing import Optional, List
from datetime import datetime, date
from dataclasses import dataclass
from django.db import models
from django.db.models import OuterRef, Subquery, ForeignKey, DO_NOTHING, SET_NULL
from django.contrib.postgres.fields import ArrayField


class MonitoringSnapshot(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField()
    latest_getter_run_id = models.BigIntegerField()


class AbstractMetricsRecord(models.Model):
    class Meta:
        abstract = True

    snapshot = models.ForeignKey(MonitoringSnapshot, on_delete=models.CASCADE)
    # timestamp is a copy of snapshot.timestamp for easier / more efficient queries
    timestamp = models.DateTimeField()

    identifier_fields: List[str]  # override in subclasses

    @classmethod
    def get_records_at(cls, at: datetime):
        """
        Return the single most recent record for each unique identifier before
        the given timestamp.
        """
        filtered_queryset = cls.objects.filter(timestamp__lte=at)

        # This query returns the single most recent record for each unique identifier
        # (e.g. Publisher IDs, Funder org-ids, SourceFile identifiers).
        # Due to the limits of chaining queries of different kinds in the Django ORM,
        # this query first finds the primary key ids of the desired records,
        # before fetching the complete records as a snapshot.
        latest_record_pks = (
            # First find all the unique identifiers that exist
            # `filtered_queryset` is all past records up until the snapshot date.
            filtered_queryset.values(*cls.identifier_fields)
            .distinct(*cls.identifier_fields)
            # At this point the query is just a list of unique identifiers.
            # Then for each unique identifier, find the record with the most recent timestamp.
            .annotate(
                latest_record=Subquery(
                    filtered_queryset.filter(
                        # Using OuterRef to enable the inner subquery to filter
                        # on the identifier fields in the outer query.
                        **{idf: OuterRef(idf) for idf in cls.identifier_fields}
                    )
                    # Get the primary key id of the one most recent record.
                    # Note: Using [:1] to return a QuerySet of length one
                    # instead of [0] because [0] can't be used in subqueries.
                    .order_by("-timestamp")[:1].values("pk"),
                    output_field=ForeignKey(cls, on_delete=DO_NOTHING),
                )
            )
            .values_list("latest_record", flat=True)
        )

        records = cls.objects.filter(pk__in=latest_record_pks)
        return records


@dataclass
class DatasetMetrics:
    """
    Metrics global to the whole dataset i.e. the Latest best at the time of recording.
    """

    total_grants: int
    total_grants_to_individuals: int
    total_amount_awarded_gbp: int
    total_publishers: int
    total_funders: int
    total_recipient_individuals: int
    total_recipient_organisations: int


class DatasetMetricsRecord(AbstractMetricsRecord):
    identifier_fields = ["timestamp"]

    metrics = models.JSONField()


@dataclass
class PublisherMetrics:
    total_grants: int
    total_gbp: float
    total_funders: int
    total_recipient_individuals: int
    total_recipient_organisations: int


class PublisherMetricsRecord(AbstractMetricsRecord):
    identifier_fields = ["publisher_prefix"]

    publisher_prefix = models.TextField()
    metrics = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["publisher_prefix"]),
            models.Index(fields=["publisher_prefix", "timestamp"]),
        ]

    def __str__(self):
        return f"<PublisherMetrics {self.timestamp} {self.publisher_prefix}>"


@dataclass
class FunderMetrics:
    total_grants: int
    total_gbp: Optional[float]  # May be None for non-UK funders with no GBP grants
    latest_award_date: date
    earliest_award_date: date


class FunderMetricsRecord(AbstractMetricsRecord):
    identifier_fields = ["funder_org_id"]

    funder_org_id = models.TextField()
    funder_non_primary_org_ids = ArrayField(models.TextField(), blank=True)
    metrics = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["funder_org_id"]),
            models.Index(fields=["funder_org_id", "timestamp"]),
        ]

    def __str__(self):
        return f"<FunderMetrics {self.timestamp} {self.funder_org_id} {self.funder_non_primary_org_ids}>"


@dataclass
class SourceFileMetrics:
    # None if never successfully downloaded
    last_successful_download_at: Optional[datetime]
    last_download_attempt_at: datetime
    last_download_attempt_download_url: str
    last_download_attempt_downloaded: bool
    last_download_attempt_valid: Optional[bool]
    last_download_attempt_error: str
    days_since_last_successful_download: int
    # New metrics added later must be optional so that the serialiser can still work with older records
    last_download_attempt_access_url: Optional[str]
    last_successful_download_was_at_least_7_days_ago: Optional[bool]


class SourceFileMetricsRecord(AbstractMetricsRecord):
    identifier_fields = ["publisher_prefix", "sourcefile_identifier"]

    publisher_prefix = models.TextField()
    sourcefile_identifier = models.TextField()
    sourcefile_url = models.TextField()
    metrics = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["publisher_prefix", "sourcefile_identifier"]),
            models.Index(
                fields=["publisher_prefix", "sourcefile_identifier", "timestamp"]
            ),
        ]

    def __str__(self):
        return f"<SourceFileMetrics {self.timestamp} {self.publisher_prefix} {self.sourcefile_identifier}>"
