from rest_framework import serializers

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
    org_id = serializers.CharField(max_length=200)
    name = serializers.CharField(allow_blank=True, required=False)


class OrganisationSerializer(serializers.Serializer):
    org_id = serializers.CharField(max_length=200)  # TODO: validate org id?
    funder = FunderSerializer(required=False)
    recipient = RecipientSerializer(required=False)
    publisher = PublisherSerializer(required=False)
