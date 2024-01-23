from django.conf import settings
from rest_framework import serializers
from rest_framework.reverse import reverse
from django.templatetags.static import static
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from rest_framework_dataclasses.serializers import DataclassSerializer

import db.models as db
from . import models


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
    avg = serializers.FloatField()
    max = serializers.FloatField()
    min = serializers.FloatField()
    total = serializers.FloatField()
    grants = serializers.IntegerField()


class OrganisationAggregateSerializer(serializers.Serializer):
    grants = serializers.IntegerField()
    currencies = serializers.DictField(child=OrganisationAggregateCurrencySerializer())


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


class GrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Grant
        exclude = ["id", "getter_run", "latest", "source_file", "additional_data"]

    data = GrantDataField()

    publisher = serializers.SerializerMethodField()
    recipients = serializers.SerializerMethodField()
    funders = serializers.SerializerMethodField()

    @extend_schema_field(OrganisationRefSerializer)
    def get_publisher(self, grant):
        return OrganisationRefSerializer(
            models.OrganisationRef(grant.publisher.org_id), context=self.context
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
