from rest_framework import serializers
from rest_framework.reverse import reverse

import db.models as db
from . import models


class GetterRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.GetterRun
        fields = ["datetime", "archived"]


class OrganisationRefSerializer(serializers.Serializer):
    org_id = serializers.CharField()
    self = serializers.SerializerMethodField()

    def get_self(self, org):
        """Get the URL to this object's detail."""
        return reverse(
            "api:organisation-detail",
            kwargs={"org_id": org.org_id},
            request=self.context.get("request"),
        )


class GrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Grant
        exclude = ["id", "getter_run", "latest", "source_file"]

    self = serializers.SerializerMethodField()
    publisher = serializers.SerializerMethodField()
    recipients = serializers.SerializerMethodField()
    funders = serializers.SerializerMethodField()

    def get_self(self, grant):
        """Get the URL to this object's detail."""
        return reverse(
            "api:grant-detail",
            kwargs={"grant_id": grant.grant_id},
            request=self.context.get("request"),
        )

    def get_publisher(self, grant):
        return OrganisationRefSerializer(
            models.OrganisationRef(grant.publisher.org_id), context=self.context
        ).data

    def get_recipients(self, grant):
        return [
            OrganisationRefSerializer(
                models.OrganisationRef(recipient["id"]), context=self.context
            ).data
            for recipient in grant.data.get("recipientOrganization", [])
        ]

    def get_funders(self, grant):
        return [
            OrganisationRefSerializer(
                models.OrganisationRef(funder["id"]), context=self.context
            ).data
            for funder in grant.data.get("fundingOrganization", [])
        ]


class FunderSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Funder
        exclude = ["id"]


class RecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Recipient
        exclude = ["id"]


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Publisher
        exclude = ["id", "getter_run"]


class OrganisationListSerializer(serializers.Serializer):
    self = serializers.SerializerMethodField()
    org_id = serializers.CharField(max_length=200)
    name = serializers.CharField(allow_blank=True, required=False)

    def get_self(self, org):
        """Get the URL to this object's detail."""
        request = self.context.get("request")
        return reverse(
            "api:organisation-detail", kwargs={"org_id": org["org_id"]}, request=request
        )


class OrganisationSerializer(serializers.Serializer):
    self = serializers.SerializerMethodField()
    org_id = serializers.CharField(max_length=200)
    grants_made = serializers.SerializerMethodField()
    grants_received = serializers.SerializerMethodField()
    funder = FunderSerializer(required=False)
    recipient = RecipientSerializer(required=False)
    publisher = PublisherSerializer(required=False)

    def get_self(self, org):
        """Get the URL to this object's detail."""
        request = self.context.get("request")
        return reverse(
            "api:organisation-detail", kwargs={"org_id": org.org_id}, request=request
        )

    def get_grants_made(self, org):
        return reverse(
            "api:organisation-grants-made",
            kwargs={"org_id": org.org_id},
            request=self.context.get("request"),
        )

    def get_grants_received(self, org):
        return reverse(
            "api:organisation-grants-received",
            kwargs={"org_id": org.org_id},
            request=self.context.get("request"),
        )
