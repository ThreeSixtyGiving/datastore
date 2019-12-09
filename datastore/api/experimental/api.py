from rest_framework import generics

from rest_framework.pagination import LimitOffsetPagination
from rest_framework import filters

import django_filters.rest_framework

import db.models as db
from api.experimental import serializers


class CurrentLatestGrantsPaginator(LimitOffsetPagination):
    default_limit = 360


class CurrentLatestGrants(generics.ListAPIView):
    serializer_class = serializers.GrantSerializer
    pagination_class = CurrentLatestGrantsPaginator

    search_fields = ('$data',)
    filter_fields = ('grant_id', 'id')
    filter_backends = (filters.SearchFilter, django_filters.rest_framework.DjangoFilterBackend)

    def get_queryset(self):
        return db.Latest.objects.get(
            series=db.Latest.CURRENT).grant_set.all()
