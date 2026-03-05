from django.conf import settings
from rest_framework import serializers
from rest_framework.reverse import reverse
from django.templatetags.static import static
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from rest_framework_dataclasses.serializers import DataclassSerializer
from typing import Optional

import db.models as db
from api.org import models


class OrganisationRefSerializer(DataclassSerializer):
    class Meta:
        dataclass = models.OrganisationRef

    self = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.URI)
    def get_self(self, org):
        """Get the URL to this object's detail."""
        return reverse(
            "api:organisation-detail",
            kwargs={"org_id": org.org_id},
            request=self.context.get("request"),
        )


class OrganisationAggregateCurrencySerializer(serializers.Serializer):
    # NOTE: avg to be deprecated in version 2
    # https://github.com/ThreeSixtyGiving/datastore/issues/292
    avg = serializers.FloatField()
    max = serializers.FloatField()
    min = serializers.FloatField()
    total = serializers.FloatField()
    grants = serializers.IntegerField()


class OrganisationAggregateSerializer(serializers.Serializer):
    grants = serializers.IntegerField()

    earliest_grant_date = serializers.SerializerMethodField()
    latest_grant_date = serializers.SerializerMethodField()

    currencies = serializers.SerializerMethodField()

    def get_earliest_grant_date(self, aggregate) -> Optional[str]:
        return aggregate.get("minAwardDate")

    def get_latest_grant_date(self, aggregate) -> Optional[str]:
        return aggregate.get("maxAwardDate")

    # NOTE: This field will be deprecated in future version in favour of
    # the direct representation from the entitiy model's aggregate data.
    # This method is to provide API v1 compatibility.
    def get_currencies(self, org):
        def serialize_currencies(currencies):
            """serialise the nested data using OrganisationAggregateCurrencySerializer"""
            ret = {}
            for currency in currencies.keys():
                serialize = OrganisationAggregateCurrencySerializer(
                    currencies[currency]
                )
                ret[currency] = serialize.data
            return ret

        def combine_currencies_org_ind(currency):
            """recombine currency stats from both recipient_org and recipient_ind"""
            combined_grants = (
                recipient_org_currencies[currency]["grants"]
                + recipient_ind_currencies[currency]["grants"]
            )
            combined_total = (
                recipient_org_currencies[currency]["total"]
                + recipient_ind_currencies[currency]["total"]
            )

            # Calculate the new average
            if combined_grants > 0:
                combined_avg = combined_total / combined_grants
            else:
                combined_avg = 0.0

            # Determine the new min and max using direct key access
            combined_min = min(
                recipient_org_currencies[currency]["min"],
                recipient_ind_currencies[currency]["min"],
            )
            combined_max = max(
                recipient_org_currencies[currency]["max"],
                recipient_ind_currencies[currency]["max"],
            )
            ret = {
                "min": combined_min,
                "max": combined_max,
                "avg": combined_avg,
                "grants": combined_grants,
                "total": combined_total,
            }
            return ret

        # Separate out the currencies from e.g.
        # {
        #  { GBP: { recipient_ind: { avg, max, min }, recipient_org: { avg, max, min },
        #  { EUR: { recipient_ind: { avg, max, min },
        # }
        # and turn them into:
        # recipient_org_currencies = { GBP : { avg, max, min .. }, USD: { avg, max, min ... } ..  }
        # recipient_ind_currencies = { EUR : { avg, max, min ... },  ... }
        recipient_org_currencies = {}
        recipient_ind_currencies = {}

        for currency in org["currencies"].keys():
            if currency_stats := org["currencies"][currency].get("recipient_org"):
                recipient_org_currencies[currency] = currency_stats

            if currency_stats := org["currencies"][currency].get("recipient_ind"):
                recipient_ind_currencies[currency] = currency_stats

        # The easy cases (and most common) where the funder justs funds recipient_org_currencies
        # return those currency stats
        if recipient_org_currencies and not recipient_ind_currencies:
            return serialize_currencies(recipient_org_currencies)

        # Or only funds recipient_ind_currencies
        # return those currency stats
        if recipient_ind_currencies and not recipient_org_currencies:
            return serialize_currencies(recipient_ind_currencies)

        # If funds both inds and orgs we need to be aware of the possibility of any
        # mix of currencies with any mix of ind or org recipients
        if recipient_org_currencies and recipient_ind_currencies:
            ret = {}

            set_recipient_org_currencies = set(recipient_org_currencies.keys())
            set_recipient_ind_currencies = set(recipient_ind_currencies.keys())

            common_currencies = list(
                set_recipient_org_currencies.intersection(set_recipient_ind_currencies)
            )
            currencies_only_in_recipient_org_currencies = list(
                set_recipient_org_currencies.difference(set_recipient_ind_currencies)
            )
            currencies_only_in_recipient_ind_currencies = list(
                set_recipient_ind_currencies.difference(set_recipient_org_currencies)
            )

            # Combine the combinations, either combining org/ind where they are
            # in the same currency or when not extracting the stats and adding
            # them to the output.

            for currency in common_currencies:
                ret[currency] = combine_currencies_org_ind(currency)

            for currency in currencies_only_in_recipient_org_currencies:
                ret[currency] = recipient_org_currencies[currency]

            for currency in currencies_only_in_recipient_ind_currencies:
                ret[currency] = recipient_ind_currencies[currency]

            return serialize_currencies(ret)

        raise Exception(f"The organisation didn't have the required data {org}")


class OrganisationFunderSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Funder
        fields = ["aggregate"]

    aggregate = OrganisationAggregateSerializer()


class OrganisationRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Recipient
        fields = ["aggregate"]

    aggregate = OrganisationAggregateSerializer()


class OrganisationPublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Publisher
        fields = ["prefix"]


class OrganisationListSerializer(serializers.Serializer):
    self = serializers.SerializerMethodField()
    org_id = serializers.CharField(max_length=200)
    name = serializers.CharField(allow_blank=True, required=False)

    @extend_schema_field(OpenApiTypes.URI)
    def get_self(self, org):
        """Get the URL to this object's detail."""
        request = self.context.get("request")
        return reverse(
            "api:organisation-detail", kwargs={"org_id": org["org_id"]}, request=request
        )


class OrganisationSerializer(DataclassSerializer):
    class Meta:
        dataclass = models.Organisation

    self = serializers.SerializerMethodField()
    grants_made = serializers.SerializerMethodField()
    grants_received = serializers.SerializerMethodField()
    funder = OrganisationFunderSerializer(required=False)
    recipient = OrganisationRecipientSerializer(required=False)
    publisher = OrganisationPublisherSerializer(required=False)

    @extend_schema_field(OpenApiTypes.URI)
    def get_self(self, org):
        """Get the URL to this object's detail."""
        request = self.context.get("request")
        return reverse(
            "api:organisation-detail", kwargs={"org_id": org.org_id}, request=request
        )

    @extend_schema_field(OpenApiTypes.URI)
    def get_grants_made(self, org):
        return reverse(
            "api:organisation-grants-made",
            kwargs={"org_id": org.org_id},
            request=self.context.get("request"),
        )

    @extend_schema_field(OpenApiTypes.URI)
    def get_grants_received(self, org):
        return reverse(
            "api:organisation-grants-received",
            kwargs={"org_id": org.org_id},
            request=self.context.get("request"),
        )


# Reference the external static schema
@extend_schema_field({"$ref": static(settings.TSG_OPENAPI_SCHEMA_STATICFILE)})
class GrantDataField(serializers.JSONField):
    """A JSONField annotated with 360 Giving's Grant data schema."""

    pass


class GrantLicenseSerializer(DataclassSerializer):
    class Meta:
        dataclass = models.GrantLicense

    url = serializers.URLField()


class GrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Grant
        fields = [
            "grant_id",
            "data",
            "data_license",
            "publisher",
            "recipients",
            "funders",
        ]

    data = GrantDataField()

    data_license = serializers.SerializerMethodField()

    publisher = serializers.SerializerMethodField()
    recipients = serializers.SerializerMethodField()
    funders = serializers.SerializerMethodField()

    @extend_schema_field(GrantLicenseSerializer)
    def get_data_license(self, grant):
        return GrantLicenseSerializer(
            models.GrantLicense(
                url=grant.source_file.data.get("license"),
                name=grant.source_file.data.get("license_name"),
            )
        ).data

    @extend_schema_field(OrganisationRefSerializer)
    def get_publisher(self, grant):
        return OrganisationRefSerializer(
            models.OrganisationRef(grant.publisher_org_id), context=self.context
        ).data

    @extend_schema_field(OrganisationRefSerializer(many=True))
    def get_recipients(self, grant):
        return [
            OrganisationRefSerializer(
                models.OrganisationRef(recipient["id"]), context=self.context
            ).data
            for recipient in grant.data.get("recipientOrganization", [])
        ]

    @extend_schema_field(OrganisationRefSerializer(many=True))
    def get_funders(self, grant):
        return [
            OrganisationRefSerializer(
                models.OrganisationRef(funder["id"]), context=self.context
            ).data
            for funder in grant.data.get("fundingOrganization", [])
        ]
