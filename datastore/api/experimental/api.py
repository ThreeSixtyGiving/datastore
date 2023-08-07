import django_filters.rest_framework
from rest_framework import filters, generics
from rest_framework.pagination import LimitOffsetPagination

import db.models as db
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


class OrganisationRetrieveView(generics.RetrieveAPIView):
    lookup_field = "org_id"

    def get_serializer(self, instance):
        if isinstance(instance, db.Funder):
            return serializers.FunderSerializer(instance)

        elif isinstance(instance, db.Recipient):
            return serializers.RecipientSerializer(instance)

        else:
            raise ValueError("OrganisationRetrieveView expected Funder or Recipient")

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
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}

        funder_queryset = self.filter_queryset(db.Funder.objects.all())
        recipient_queryset = self.filter_queryset(db.Recipient.objects.all())

        # First try Funder
        try:
            obj = funder_queryset.get(**filter_kwargs)

        except db.Funder.DoesNotExist:
            # otherwise Recipient, or 404
            obj = generics.get_object_or_404(recipient_queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj