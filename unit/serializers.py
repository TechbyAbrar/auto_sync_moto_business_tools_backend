from rest_framework import serializers
from .models import RegisterUnit, ScheduleService, SellUnit


class RegisterUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegisterUnit
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'registrar')

    def validate_year(self, value):
        if value < 1886:
            raise serializers.ValidationError("Year must be 1886 or later.")
        return value

    def validate_vin(self, value):
        vin_length = len(value)
        if vin_length < 11 or vin_length > 25:
            raise serializers.ValidationError("VIN must be between 11 and 25 characters.")
        return value

    def create(self, validated_data):
        request = self.context.get("request")

        # Force registrar to be the logged-in user
        if request and request.user.is_authenticated:
            validated_data["registrar"] = request.user

        return super().create(validated_data)

# services
class ScheduleServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleService
        fields = [
            "id",
            "unit",
            "details",
            "location",
            "appointment_date",
            "has_serviced_before",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# sell unit
class SellUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellUnit
        fields = ["id", "unit", "seller", "additional_details", "created_at", "updated_at"]
        read_only_fields = ["id", "seller", "created_at", "updated_at"]

    def validate_unit(self, unit):
        request = self.context["request"]

        if unit.registrar != request.user:
            raise serializers.ValidationError("You cannot sell a unit you do not own.")

        if SellUnit.objects.filter(unit=unit, seller=request.user).exists():
            raise serializers.ValidationError("You already listed this unit for sale.")

        return unit