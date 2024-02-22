import django_filters.rest_framework
import rest_framework.exceptions
from django.http import Http404
from rest_framework import generics
from rest_framework.pagination import LimitOffsetPagination

import db.models as db
from . import models
from . import serializers


class OrganisationsPagination(LimitOffsetPagination):
    default_limit = 1000


class OrganisationListView(generics.ListAPIView):
    serializer_class = serializers.OrganisationListSerializer
    pagination_class = OrganisationsPagination

    def get_queryset(self):
        fields = ["org_id", "name"]
        return (
            db.Publisher.objects.filter(getter_run__in=db.GetterRun.objects.in_use())
            .values(*fields)
            .union(db.Funder.objects.all().values(*fields))
            .union(db.Recipient.objects.all().values(*fields))
        )


class OrganisationDetailView(generics.RetrieveAPIView):
    """
    Get details about the given organisation.

    The response is divided into three sub-objects:
    funder, recipient and publisher
    for each of the roles the organisation takes.

    If an organisation doesn't taken on a role the value will be null,
    e.g. it's a recipient of grants but not a funder or publisher, funder and
    publisher will be null.
    """

    lookup_field = "org_id"
    serializer_class = serializers.OrganisationSerializer

    def get_object(self):
        """
        Return the object the view is displaying.

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
        publisher_queryset = self.filter_queryset(
            db.Publisher.objects.filter(getter_run__in=db.GetterRun.objects.in_use())
        )

        organisation = models.Organisation.get(
            org_id,
            funder_queryset=funder_queryset,
            recipient_queryset=recipient_queryset,
            publisher_queryset=publisher_queryset,
        )

        if not organisation:
            raise Http404

        return organisation


class GrantsPagination(LimitOffsetPagination):
    default_limit = 60


class OrganisationGrantsMadeView(generics.ListAPIView):
    """
    Get a list of all the grants made by the given organisation (funder).

    For grant data schema, see the 360G schema: https://standard.threesixtygiving.org/en/latest/_static/docson/index.html#../360-giving-schema.json
    """

    serializer_class = serializers.GrantSerializer
    pagination_class = GrantsPagination
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]

    def get_queryset(self):
        org_id = self.kwargs.get("org_id")

        # Raise 404 if the Org doesn't exist
        if not models.Organisation.exists(org_id):
            raise rest_framework.exceptions.NotFound()

        return db.Latest.grants().filter(
            data__fundingOrganization__contains=[{"id": org_id}]
        )


class OrganisationGrantsReceivedView(generics.ListAPIView):
    """
    Get a list of all the grants recieved by the given organisation (recipient).

    For grant data schema, see the 360G schema: https://standard.threesixtygiving.org/en/latest/_static/docson/index.html#../360-giving-schema.json
    """

    serializer_class = serializers.GrantSerializer
    pagination_class = GrantsPagination
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]

    def get_queryset(self):
        org_id = self.kwargs.get("org_id")

        # Raise 404 if the Org doesn't exist
        if not models.Organisation.exists(org_id):
            raise rest_framework.exceptions.NotFound()

        return db.Latest.grants().filter(
            data__recipientOrganization__contains=[{"id": org_id}]
        )
