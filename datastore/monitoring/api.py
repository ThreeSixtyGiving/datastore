import datetime

from django.db.models import OuterRef, Subquery, ForeignKey, DO_NOTHING
from rest_framework.generics import ListAPIView
from rest_framework.settings import api_settings
from rest_framework_csv.renderers import CSVRenderer

from monitoring.models import (
    PublisherMetricsRecord,
    FunderMetricsRecord,
    SourceFileMetricsRecord,
)
from monitoring.serializers import (
    PublisherMetricsRecordSerializer,
    FunderMetricsRecordSerializer,
    SourceFileMetricsRecordSerializer,
)


class SnapshotAPIView(ListAPIView):
    identifier_fields = []  # override in subclasses

    def get_queryset(self):
        snapshot_date = self.kwargs.get("snapshot_date")
        queryset = super().get_queryset()

        if snapshot_date is None:
            snapshot_date = datetime.date.today()

        # Find the latest snapshot on the given day, or earlier
        snapshot_date_end_of_day = datetime.datetime.combine(
            datetime.date.fromisoformat(snapshot_date), datetime.datetime.max.time()
        )
        filtered_queryset = queryset.filter(timestamp__lte=snapshot_date_end_of_day)

        ident_filter = {idf: OuterRef(idf) for idf in self.identifier_fields}

        # This is not the most efficient query, but it's only meant to be accessed occasionally, and still renders in ms
        latest_record_pks = (
            queryset.values(*self.identifier_fields)
            .distinct(*self.identifier_fields)
            .annotate(
                # For each unique identifier, find the most recent timestamp in the filtered set
                latest_record=Subquery(
                    filtered_queryset.filter(**ident_filter)
                    .order_by("-timestamp")[:1]
                    .values("pk"),
                    output_field=ForeignKey(queryset.model, on_delete=DO_NOTHING),
                )
            )
            .values_list("latest_record", flat=True)
        )

        snapshot = queryset.filter(pk__in=latest_record_pks)
        return snapshot

        # snapshot = (
        #    queryset.filter(
        #        pk__in=Subquery(
        #            queryset.filter(**ident_filter)
        #            .order_by("-timestamp")[:1]
        #            .values("pk")
        #        )
        #    )
        #    # We don't need to sort by identifiers but
        #    # PostgreSQL requires order by fields must match distinct fields.
        #    .order_by("-timestamp", *self.identifier_fields)
        #    # Distinct to only return a single (latest) snapshot for each identifier.
        #    .distinct(*self.identifier_fields)
        # )

        # return snapshot


class PublisherMetricsSnapshotAPIView(SnapshotAPIView):
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)
    serializer_class = PublisherMetricsRecordSerializer

    queryset = PublisherMetricsRecord.objects.all()
    identifier_fields = ["publisher_prefix"]


class FunderMetricsSnapshotAPIView(SnapshotAPIView):
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)
    serializer_class = FunderMetricsRecordSerializer

    queryset = FunderMetricsRecord.objects.all()
    identifier_fields = ["funder_org_id"]


class SourceFileMetricsSnapshotAPIView(SnapshotAPIView):
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)
    serializer_class = SourceFileMetricsRecordSerializer

    queryset = SourceFileMetricsRecord.objects.all()
    identifier_fields = ["publisher_prefix", "sourcefile_identifier"]
