from rest_framework import serializers

import db.models as db


class SourcesSerializer(serializers.ModelSerializer):
    id = serializers.JSONField(source="data.identifier")
    title = serializers.JSONField(source="data.title")
    license = serializers.JSONField(source="data.license_name")
    datagetter_data = serializers.JSONField()
    modified = serializers.JSONField(source="data.modified")
    distribution = serializers.JSONField(source="get_distribution")
    quality = serializers.JSONField()
    aggregate = serializers.JSONField()

    class Meta:
        model = db.SourceFile
        fields = (
            "id",
            "title",
            "license",
            "datagetter_data",
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
    lastLastModified = serializers.CharField(source="get_last_last_modified")

    class Meta:
        model = db.Publisher
        fields = (
            "name",
            "logo",
            "prefix",
            "lastLastModified",
            "website",
            "aggregate",
            "quality",
        )


class PublisherSerializer(PublishersSerializer):

    # Same as Publishers but with added `files`
    files = SourcesSerializer(source="get_sourcefiles", many=True)
    lastLastModified = serializers.CharField(source="get_last_last_modified")

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
            "lastLastModified",
        )
