from rest_framework import serializers

import db.models as db


class SourcesSerializer(serializers.ModelSerializer):
    id = serializers.JSONField(source="data.identifier")
    datagetter_data = serializers.JSONField()
    modified = serializers.JSONField(source="data.modified")
    grants = serializers.IntegerField()
    distribution = serializers.JSONField(source="get_distribution")
    quality = serializers.JSONField()
    aggregate = serializers.JSONField()

    class Meta:
        model = db.SourceFile
        fields = (
            "id",
            "datagetter_data",
            "grants",
            "distribution",
            "modified",
            "quality",
            "aggregate",
        )


class PublishersSerializer(serializers.ModelSerializer):
    name = serializers.JSONField(source="data.name")
    logo = serializers.JSONField(source="data.logo")
    prefix = serializers.JSONField(source="data.prefix")
    website = serializers.JSONField(source="data.website")
    aggregate = serializers.JSONField()
    quality = serializers.JSONField()

    class Meta:
        model = db.Publisher
        fields = (
            "name",
            "logo",
            "prefix",
            "website",
            "aggregate",
            "quality",
        )


class PublisherSerializer(PublishersSerializer):

    # Same as Publishers but with added `files`
    files = SourcesSerializer(source="get_sourcefiles", many=True)

    class Meta:
        model = db.Publisher
        fields = (
            "name",
            "logo",
            "prefix",
            "website",
            "aggregate",
            "quality",
            "files",
        )
