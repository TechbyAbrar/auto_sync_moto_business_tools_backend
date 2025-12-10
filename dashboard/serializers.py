from rest_framework import serializers
from account.models import UserAuth


class UserListSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField()
    phone = serializers.CharField(allow_null=True, allow_blank=True)
    address = serializers.CharField(allow_null=True, allow_blank=True)
    dob = serializers.DateField(allow_null=True)
    zip_code = serializers.CharField(allow_null=True, allow_blank=True)
    
    def get_full_name(self, obj):
        first = obj.get('first_name', '') or ''
        last = obj.get('last_name', '') or ''
        return f"{first} {last}".strip() or 'N/A'

class DashboardStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField(min_value=0)
    appointments_today = serializers.IntegerField(min_value=0)
    sales_today = serializers.IntegerField(min_value=0)
    
    current_month_appointments = serializers.IntegerField()
    last_month_appointments = serializers.IntegerField()
    
    users = UserListSerializer(many=True)


class UserDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = UserAuth
        fields = [
            "user_id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "address",
            "zip_code",
            "dob",
            "profile_pic",
            "profile_pic_url",
            "is_verified",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()
