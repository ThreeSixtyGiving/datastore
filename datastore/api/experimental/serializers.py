from rest_framework import serializers
from rest_framework.reverse import reverse

import db.models as db


class GetterRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.GetterRun
        fields = ["datetime", "archived"]


class GrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Grant
        fields = "__all__"


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
        exclude = ["id"]

    getter_run = GetterRunSerializer()


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
    org_id = serializers.CharField(max_length=200)  # TODO: validate org id?
    grants_made = serializers.SerializerMethodField()
    grants_received = serializers.SerializerMethodField()
    funder = FunderSerializer(required=False)
    recipient = RecipientSerializer(required=False)
    publisher = PublisherSerializer(required=False)

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
