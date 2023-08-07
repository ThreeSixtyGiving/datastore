from rest_framework import serializers

import db.models as db


class GrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Grant
        fields = "__all__"


class FunderSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Funder
        fields = "__all__"


class RecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Recipient
        fields = "__all__"