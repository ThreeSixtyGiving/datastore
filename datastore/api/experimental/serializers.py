from rest_framework import serializers

import db.models as db


class GrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Grant
        fields = ('__all__')
