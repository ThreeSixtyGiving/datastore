from rest_framework.serializers import ModelSerializer

from additional_data.models import IMDWardLookup


class IMDWardLookupSerializer(ModelSerializer):
    class Meta:
        model = IMDWardLookup
        exclude = ["id"]
