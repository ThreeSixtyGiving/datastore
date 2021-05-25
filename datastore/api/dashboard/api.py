import django_filters.rest_framework
from rest_framework import filters, generics
import db.models as db
from api.dashboard import serializers
from api.dashboard.permissions import ReadOnly


class Publishers(generics.ListAPIView):
    serializer_class = serializers.PublishersSerializer
    permission_classes = [ReadOnly]

    filter_backends = (
        filters.SearchFilter,
        django_filters.rest_framework.DjangoFilterBackend,
        filters.OrderingFilter,
    )

    search_fields = ("^data__name",)
    filterset_fields = ["name", "prefix"]

    ordering_fields = ["data__name"]

    def get_queryset(self):
        return db.Publisher.objects.filter(getter_run=db.GetterRun.objects.last())


class Sources(generics.ListAPIView):
    serializer_class = serializers.SourcesSerializer
    #  pagination_class = CurrentLatestGrantsPaginator

    def get_queryset(self):
        return db.SourceFile.objects.filter(getter_run=db.GetterRun.objects.last())
