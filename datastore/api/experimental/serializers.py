from rest_framework import serializers

import db.models as db


class CurrentLatestGrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Grant
        exclude = ["id", "getter_run", "latest", "source_file"]
