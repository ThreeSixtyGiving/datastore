import logging
from dataclasses import dataclass
from datetime import datetime, date, UTC, timedelta
from typing import Optional, List, Any

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import OuterRef, Subquery, ForeignKey, DO_NOTHING, QuerySet

logger = logging.getLogger(__name__)

# The number of hours leeway when performing "within 1 days" calculations
# e.g. 24 hours + 4 hours leeway counts as "within the same day"
FUZZY_DAY_LEEWAY_HOURS = 4


class MonitoringSnapshot(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField()
    latest_getter_run_id = models.BigIntegerField()


@dataclass
class ChangedRecord:
    # At least one of start_record and/or end_record must be set
    start_record: Optional["AbstractMetricsRecord"]
    end_record: Optional["AbstractMetricsRecord"]
    changed_metrics: list[str]
    record_is_new: bool
    record_was_removed: bool


class AbstractMetricsRecord(models.Model):
    class Meta:
        abstract = True

    snapshot = models.ForeignKey(MonitoringSnapshot, on_delete=models.CASCADE)
    # timestamp is a copy of snapshot.timestamp for easier / more efficient queries
    timestamp = models.DateTimeField()
    metrics = models.JSONField()

    # Override in subclasses:
    # The (combination of) fields which uniquely identify a record e.g. funder org id
    IDENTIFIER_FIELDS: List[str]
    # The metrics for which changes should be detected
    TRACKED_METRICS: List[str]

    def get_ident(self):
        return tuple([self.__dict__[k] for k in self.IDENTIFIER_FIELDS])

    @classmethod
    def get_record_by_ident(cls, qs, ident):
        assert len(cls.IDENTIFIER_FIELDS) == len(ident)
        query = {k: v for k, v in zip(cls.IDENTIFIER_FIELDS, ident)}
        return qs.get(**query)

    @classmethod
    def get_records_with_changes_between(
        cls, from_: datetime, to: Optional[datetime]
    ) -> list[ChangedRecord]:
        if to is None:
            to = datetime.now(UTC)

        # Find "start records" within 24 hours of the beginning of the comparison time
        # (Idea: Find the latest Snapshot and use that instead of searching by records individually?)
        # Find "end records" any time between the start time and the end of the end time
        start_records = cls.get_records_at(
            from_, from_=from_ - timedelta(hours=24 + FUZZY_DAY_LEEWAY_HOURS)
        )
        end_records = cls.get_records_at(to, from_=from_)

        return cls.get_records_with_changes_between_qs(start_records, end_records)

    @classmethod
    def get_records_with_changes_between_qs(
        cls,
        start_records_qs: QuerySet["AbstractMetricsRecord"],
        end_records_qs: QuerySet["AbstractMetricsRecord"],
    ) -> list[ChangedRecord]:
        start_records = {r.get_ident(): r for r in start_records_qs}
        end_records = {r.get_ident(): r for r in end_records_qs}

        start_idents = set(start_records.keys())
        end_idents = set(end_records.keys())

        # Find the identifiers present at both start/end vs not
        common_idents = start_idents & end_idents  # set intersection

        # This dict is managed by the three helper functions below
        changed_records: dict[Any, ChangedRecord] = dict()

        # Helper functions for the change-detection algorithm below
        def track_changed_metric(
            record_ident: Any,
            changed_metric_name: str,
        ):
            """
            Create or update an existing ChangedRecord to track that the given metric has changed.
            """
            # Check if this record ident already has a ChangedRecord entry, if not => create one
            if record_ident not in changed_records:
                changed_records[record_ident] = ChangedRecord(
                    start_record=start_records[record_ident],
                    end_record=end_records[record_ident],
                    changed_metrics=list(),
                    record_is_new=False,
                    record_was_removed=False,
                )

            # Update the ChangedRecord to include the new metric
            changed_record = changed_records[record_ident]
            changed_record.changed_metrics.append(changed_metric_name)

        def track_new_record(record_ident: Any):
            changed_records[record_ident] = ChangedRecord(
                start_record=None,
                end_record=end_records[ident],
                changed_metrics=list(),
                record_is_new=True,
                record_was_removed=False,
            )

        def track_removed_record(record_ident: Any):
            changed_records[record_ident] = ChangedRecord(
                start_record=start_records[ident],
                end_record=None,
                changed_metrics=list(),
                record_is_new=False,
                record_was_removed=True,
            )

        # Helper function to decide if there is a change between two metric values
        def metric_values_are_equal(
            metric_value_start: Any, metric_value_end: Any
        ) -> bool:
            # for floating point numbers, check if they're within 0.1 to handle rounding during calculations
            # See: https://docs.python.org/3/tutorial/floatingpoint.html
            # 0.1 is chosen as the floating point numbers we're dealing with here are currencies e.g. GBP, EUR, USD
            # and 0.1 (i.e. 10 pence) seems a reasonably small amount that shouldn't trigger "a change in the value
            # of grants was noticed". This is a subjective choice, feel free to change it if issues arise.
            if type(metric_value_start) is float or type(metric_value_end) is float:
                return abs(float(metric_value_start) - float(metric_value_end)) < 0.1

            # compare non-floats
            else:
                return metric_value_start == metric_value_end

        # Change detection algorithm:

        # Create a ChangedRecord for every new record
        # i.e. a record that's present at the end_date but not at the start_date
        for ident in end_idents - common_idents:
            track_new_record(ident)

        # Create a ChangedRecord for every removed record
        # i.e. a record that's present at the start_date but not at the end_date
        for ident in start_idents - common_idents:
            track_removed_record(ident)

        # Find common records with differences in any tracked metrics
        for ident in common_idents:
            start_metrics = start_records[ident].metrics
            end_metrics = end_records[ident].metrics

            for metric_name in cls.TRACKED_METRICS:
                # Adding or removing the metric should be tracked as a change
                if metric_name in start_metrics and metric_name not in end_metrics:
                    track_changed_metric(ident, changed_metric_name=metric_name)

                elif metric_name not in start_metrics and metric_name in end_metrics:
                    track_changed_metric(ident, changed_metric_name=metric_name)

                # Check if value has changed
                # If so, track the name of the metric that changed
                elif metric_name in start_metrics and metric_name in end_metrics:
                    if not metric_values_are_equal(
                        start_metrics[metric_name], end_metrics[metric_name]
                    ):
                        track_changed_metric(ident, changed_metric_name=metric_name)

        return list(changed_records.values())

    @classmethod
    def get_records_at(cls, at: datetime, from_: Optional[datetime] = None):
        """
        Return the single most recent record for each unique identifier before
        the given timestamp.
        Note that by default this function will search all historical records
        to find one record for every unique identifier ever found in 360 data,
        not just the most recent snapshot before the `at` datetime.
        To prevent this behaviour, specify the `from_` datetime to place an
        earliest bound on when records should be searched from.
        """
        filtered_queryset = cls.objects.filter(timestamp__lte=at)

        if from_ is not None:
            filtered_queryset = filtered_queryset.filter(timestamp__gt=from_)

        # This query returns the single most recent record for each unique identifier
        # (e.g. Publisher IDs, Funder org-ids, SourceFile identifiers).
        # Due to the limits of chaining queries of different kinds in the Django ORM,
        # this query first finds the primary key ids of the desired records,
        # before fetching the complete records as a snapshot.
        latest_record_pks = (
            # First find all the unique identifiers that exist
            # `filtered_queryset` is all past records up until the snapshot date.
            filtered_queryset.values(*cls.IDENTIFIER_FIELDS)
            .distinct(*cls.IDENTIFIER_FIELDS)
            # At this point the query is just a list of unique identifiers.
            # Then for each unique identifier, find the record with the most recent timestamp.
            .annotate(
                latest_record=Subquery(
                    filtered_queryset.filter(
                        # Using OuterRef to enable the inner subquery to filter
                        # on the identifier fields in the outer query.
                        **{idf: OuterRef(idf) for idf in cls.IDENTIFIER_FIELDS}
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
    # FIXME: Currency amounts should be floats
    total_amount_awarded_gbp: int
    total_amount_awarded_eur: Optional[float]
    total_amount_awarded_usd: Optional[float]
    total_publishers: int
    total_funders: int
    total_recipient_individuals: int
    total_recipient_organisations: int


class DatasetMetricsRecord(AbstractMetricsRecord):
    # A Dataset (i.e. the result of a pipeline run) has no unique identifier
    # other than the datetime at which it was created.
    IDENTIFIER_FIELDS = ["timestamp"]


@dataclass
class PublisherMetrics:
    total_grants: int
    total_gbp: Optional[float]  # May be None for non-UK funders with no GBP grants
    total_eur: Optional[float]
    total_usd: Optional[float]
    total_funders: int
    total_recipient_individuals: int
    total_recipient_organisations: int


class PublisherMetricsRecord(AbstractMetricsRecord):
    IDENTIFIER_FIELDS = ["publisher_prefix"]

    publisher_prefix = models.TextField()

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
    total_eur: Optional[float]
    total_usd: Optional[float]
    latest_award_date: date
    earliest_award_date: date


class FunderMetricsRecord(AbstractMetricsRecord):
    IDENTIFIER_FIELDS = ["funder_org_id"]
    TRACKED_METRICS = [
        "total_grants",
        "total_gbp",
        "total_eur",
        "total_usd",
        "latest_award_date",
        "earliest_award_date",
    ]

    funder_org_id = models.TextField()
    funder_non_primary_org_ids = ArrayField(models.TextField(), blank=True)
    salesforce_id = models.TextField(null=True, blank=True)
    name = models.TextField(null=True, blank=True)
    prefix = models.TextField(null=True, blank=True)
    publisher_prefix = models.TextField(null=True, blank=True)
    publisher_prefix_combined = models.TextField(null=True, blank=True)
    org_case_safe_id = models.TextField(null=True, blank=True)
    x360_giving_publisher = models.TextField(null=True, blank=True)
    sectors = models.TextField(null=True, blank=True)
    sector_organisation_type = models.TextField(null=True, blank=True)
    sector_organisation_subtype = models.TextField(null=True, blank=True)
    authorised_domain = models.TextField(null=True, blank=True)
    self_registration_enabled = models.BooleanField(null=True, blank=True)
    first_published_date = models.DateField(null=True, blank=True)
    latest_published_date = models.DateField(null=True, blank=True)
    update_schedule = models.TextField(null=True, blank=True)
    update_method = models.TextField(null=True, blank=True)

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
    IDENTIFIER_FIELDS = ["publisher_prefix", "sourcefile_identifier"]

    publisher_prefix = models.TextField()
    sourcefile_identifier = models.TextField()
    sourcefile_url = models.TextField()

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
