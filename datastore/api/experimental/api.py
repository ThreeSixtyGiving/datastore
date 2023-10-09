from django.http import Http404
import django_filters.rest_framework
from rest_framework import filters, generics
from rest_framework.pagination import LimitOffsetPagination

import db.models as db
import api.experimental.models as api_experimental
from api.experimental import serializers


class CurrentLatestGrantsPaginator(LimitOffsetPagination):
    default_limit = 60


class CurrentLatestGrants(generics.ListAPIView):
    serializer_class = serializers.GrantSerializer
    pagination_class = CurrentLatestGrantsPaginator

    search_fields = ("$data",)
    filter_fields = ("grant_id", "id")
    filter_backends = (
        filters.SearchFilter,
        django_filters.rest_framework.DjangoFilterBackend,
    )

    def get_queryset(self):
        return db.Latest.objects.get(series=db.Latest.CURRENT).grant_set.all()


class OrganisationListPagination(LimitOffsetPagination):
    default_limit = 1000


class OrganisationListView(generics.ListAPIView):
    serializer_class = serializers.OrganisationListSerializer
    pagination_class = OrganisationListPagination

    def get_queryset(self):
        fields = ["org_id"]
        return (
            db.Publisher.objects.only(*fields)
            .union(db.Funder.objects.only(*fields))
            .union(db.Recipient.objects.only(*fields))
        )


class OrganisationRetrieveView(generics.RetrieveAPIView):
    lookup_field = "org_id"
    serializer_class = serializers.OrganisationSerializer

    def get_object(self):
        """
        Returns the object the view is displaying.

        Overridden because an organisation can either by a Funder or Recipient model.
        Based on upstream DRF GenericAPIView.get_object().
        """
        # TODO: Investigate, are there better ways of implementing this multiple-concrete-querysets-of-abstract-base-model pattern?
        #       Perhaps django-polymorphic https://django-polymorphic.readthedocs.io/
        #       or some lower-level query.

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            "Expected view %s to be called with a URL keyword argument "
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            "attribute on the view correctly."
            % (self.__class__.__name__, lookup_url_kwarg)
        )

        org_id = self.kwargs[lookup_url_kwarg]

        funder_queryset = self.filter_queryset(db.Funder.objects.all())
        recipient_queryset = self.filter_queryset(db.Recipient.objects.all())
        publisher_queryset = self.filter_queryset(db.Publisher.objects.all())

        # is org a Funder?
        try:
            funder = funder_queryset.get(org_id=org_id)

        except db.Funder.DoesNotExist:
            funder = None

        # is org a Recipient?
        try:
            recipient = recipient_queryset.get(org_id=org_id)

        except db.Recipient.DoesNotExist:
            recipient = None

        # is org a Publisher?
        try:
            publisher = publisher_queryset.filter(
                org_id=org_id, getter_run=db.GetterRun.latest()
            )[0]
        except IndexError:
            publisher = None

        if funder is None and recipient is None and publisher is None:
            raise Http404

        return api_experimental.Organisation(
            org_id=org_id, funder=funder, recipient=recipient, publisher=publisher
        )
