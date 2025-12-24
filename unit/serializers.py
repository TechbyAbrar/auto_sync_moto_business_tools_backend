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


class ScheduleServiceSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)
    email = serializers.SerializerMethodField(read_only=True)
    model_name = serializers.CharField(source="unit.model", read_only=True)
    appointment_date = serializers.DateField(required=True)

    class Meta:
        model = ScheduleService
        fields = [
            "id",
            "unit",
            "full_name",
            "email",
            "model_name",
            "location",
            "appointment_date",
            "details",
            "has_serviced_before",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "full_name", "email", "model_name", "created_at", "updated_at"]

    def get_full_name(self, obj):
        return obj.unit.registrar.get_full_name() if obj.unit and obj.unit.registrar else None

    def get_email(self, obj):
        return obj.unit.registrar.email if obj.unit and obj.unit.registrar else None

# sell unit
class SellUnitSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    model_name = serializers.CharField(source="unit.model", read_only=True)
    year = serializers.IntegerField(source="unit.year", read_only=True)
    color = serializers.CharField(source="unit.color", read_only=True)  # Make sure RegisterUnit has a color field

    class Meta:
        model = SellUnit
        fields = [
            "id",
            "unit",
            "full_name",
            "email",
            "model_name",
            "year",
            "color",
            "additional_details",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "full_name", "email", "model_name", "year", "color", "created_at", "updated_at"]

    def get_full_name(self, obj):
        return obj.seller.get_full_name()

    def get_email(self, obj):
        return obj.seller.email

    def validate_unit(self, unit):
        request = self.context["request"]

        if unit.registrar != request.user:
            raise serializers.ValidationError("You cannot sell a unit you do not own.")

        if SellUnit.objects.filter(unit=unit, seller=request.user).exists():
            raise serializers.ValidationError("You already listed this unit for sale.")

        return unit
