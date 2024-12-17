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


class ListPublisherMetricsAPIView(ListAPIView):
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)

    queryset = PublisherMetricsRecord.objects.all()
    serializer_class = PublisherMetricsRecordSerializer


class ListFunderMetricsAPIView(ListAPIView):
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)

    queryset = FunderMetricsRecord.objects.all()
    serializer_class = FunderMetricsRecordSerializer


class ListSourceFileMetricsAPIView(ListAPIView):
    renderer_classes = tuple(api_settings.DEFAULT_RENDERER_CLASSES) + (CSVRenderer,)

    queryset = SourceFileMetricsRecord.objects.all()
    serializer_class = SourceFileMetricsRecordSerializer
