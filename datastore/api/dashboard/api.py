from django.http.response import JsonResponse
from django.views import View
from django.core.cache import cache
from django.conf import settings

import django_filters.rest_framework
from rest_framework import filters, generics

import db.models as db
from api.dashboard import serializers
from api.dashboard.permissions import ReadOnly
from data_quality import quality_data


class PublisherFilters(django_filters.rest_framework.FilterSet):
    quality__hasGrantProgrammeTitle = django_filters.CharFilter(
        method="hasGrantProgrammeTitle_filter", label="hasGrantProgrammeTitle"
    )

    prefix = django_filters.CharFilter(method="hasPrefix", label="hasPrefix")

    def hasGrantProgrammeTitle_filter(self, queryset, name, value):
        return queryset.filter(quality__hasGrantProgrammeTitle__iexact=value)

    def hasPrefix(self, queryset, name, value):
        return queryset.filter(prefix__exact=value)

    class Meta:
        model = db.Publisher
        fields = ["quality__hasGrantProgrammeTitle", "prefix"]


class Publishers(generics.ListAPIView):
    serializer_class = serializers.PublishersSerializer
    permission_classes = [ReadOnly]

    filter_backends = (
        filters.SearchFilter,
        django_filters.rest_framework.DjangoFilterBackend,
        filters.OrderingFilter,
    )

    filterset_class = PublisherFilters
    search_fields = ("^data__name", "^prefix")
    ordering_fields = [
        "data__name",
    ]

    def get_queryset(self):
        return db.Publisher.objects.filter(getter_run=db.GetterRun.latest())


class Publisher(generics.RetrieveAPIView):
    lookup_field = "prefix"
    lookup_url_kwarg = "publisher_prefix"
    serializer_class = serializers.PublisherSerializer

    def get_queryset(self):
        return db.Publisher.objects.filter(getter_run=db.GetterRun.latest())


class Sources(generics.ListAPIView):
    serializer_class = serializers.SourcesSerializer
    #  pagination_class = CurrentLatestGrantsPaginator

    def get_queryset(self):
        return db.SourceFile.objects.filter(getter_run=db.GetterRun.latest())


class Overview(View):
    def get(self, *args, **kwargs):
        # If we have a cache of this uri then return that.
        # All caches are cleared if the dataload happens
        full_request_uri = self.request.build_absolute_uri()

        # Don't cache if we have ?nocache in the query
        if not self.request.GET.get("nocache") and not settings.DEBUG:
            ret = cache.get(full_request_uri)
            if ret:
                print("retuning cache")
                return JsonResponse(ret, safe=False)

        mode = "overview_%s" % self.request.GET.get("mode", "grants")

        source_file_set = db.Latest.objects.get(
            series=db.Latest.CURRENT
        ).sourcefile_set.all()

        ret = quality_data.generate_stats(mode, source_file_set)

        cache.set(full_request_uri, ret)

        return JsonResponse(ret, safe=False)
