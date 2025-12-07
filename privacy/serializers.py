# serializers.py
from rest_framework import serializers
from .models import PrivacyPolicy, AboutUs, TermsConditions, SubmitQuery


class BaseContentSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["id", "image", "description", "last_updated"]
        read_only_fields = ["id", "last_updated"]


class PrivacyPolicySerializer(BaseContentSerializer):
    class Meta(BaseContentSerializer.Meta):
        model = PrivacyPolicy


class AboutUsSerializer(BaseContentSerializer):
    class Meta(BaseContentSerializer.Meta):
        model = AboutUs


class TermsConditionsSerializer(BaseContentSerializer):
    class Meta(BaseContentSerializer.Meta):
        model = TermsConditions


class SubmitQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmitQuery
        fields = ["id", "name", "email", "message", "created_at"]
        read_only_fields = ["id", "created_at"]
