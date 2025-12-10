from rest_framework import serializers
from django.utils import timezone
from .utils import generate_username, send_otp_email
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
User = get_user_model()
from .models import UserAuth 


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, min_length=6,
        style={'input_type': 'password'}
    )
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'user_id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'username',
            'profile_pic',
            'profile_pic_url',
            'phone',
            'address',
            'zip_code',
            'dob',
            'is_verified',
            'is_active',
            'is_staff',
            'is_superuser',
            'created_at',
            'updated_at',
            'password',
        ]
        read_only_fields = ('user_id', 'is_verified', 'is_active', 'is_staff', 'is_superuser', 'created_at', 'updated_at')

    def get_full_name(self, obj):
        return obj.get_full_name()

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = self.Meta.model(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.updated_at = timezone.now()
        instance.save()
        return instance



# update profile
class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAuth
        fields = [
            "first_name",
            "last_name",
            "email",
            "username",
            "profile_pic",
            "dob",
            "phone",
            "address",
            "zip_code",
        ]
        extra_kwargs = {
            "email": {"required": True},
            "username": {"required": False, "allow_blank": True},
        }

    def validate_email(self, value):
        user = self.instance
        if UserAuth.objects.exclude(user_id=user.user_id).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'user_id', 'first_name', 'last_name', 'email', 'phone', 'address',
            'zip_code', 'dob', 'password', 'confirm_password'
        ]
        read_only_fields = ['user_id']

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("confirm_password"):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('confirm_password')

        password = validated_data.pop('password')
        email = validated_data.pop('email')  # remove email to avoid duplication

        username = generate_username(email)

        full_name = f"{validated_data.get('first_name')} {validated_data.get('last_name')}"

        user = User(
            username=username,
            email=email,
            **validated_data   # now safe
        )

        user.set_password(password)
        user.full_name = full_name
        user.set_otp()
        user.save()

        send_otp_email(user.email, user.otp)
        return user




class VerifyEmailOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, write_only=True)

    def validate_otp(self, value):
        """
        Only OTP is required. We fetch the first active, unverified user with this OTP.
        """
        now = timezone.now()

        try:
            # Fetch minimal fields, unverified users only
            user = User.objects.only(
                "user_id", "otp", "otp_expired", "is_verified", "email"
            ).filter(is_verified=False, otp=value, otp_expired__gte=now).first()

            if not user:
                raise serializers.ValidationError("Invalid or expired OTP.")

        except Exception:
            raise serializers.ValidationError("OTP validation failed.")

        self.context["user"] = user
        return value

class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.only('email').get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        self.context['user'] = user
        return value

    def save(self):
        user = self.context['user']
        user.set_otp()
        user.save(update_fields=['otp', 'otp_expired'])
        send_otp_email(user.email, user.otp)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("User account is inactive.")

        attrs['user'] = user
        return attrs


class ForgetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.only('email', 'otp', 'otp_expired').get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        self.context['user'] = user
        return value

    def save(self):
        user = self.context['user']
        user.set_otp()
        user.save(update_fields=['otp', 'otp_expired'])
        send_otp_email(user.email, user.otp)
        return user


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        new_password = attrs.get("new_password")
        confirm_password = attrs.get("confirm_password")

        if new_password != confirm_password:
            raise serializers.ValidationError("Passwords do not match.")

        # Get the user from the request context (access token)
        user = self.context.get("user")
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("User authentication required.")

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user




class VerifyForgetPasswordOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, write_only=True)

    def validate_otp(self, value):
        try:
            # Only consider verified users
            user = User.objects.only('user_id', 'email', 'otp', 'otp_expired', 'is_verified') \
                            .get(otp=value, is_verified=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired OTP.")

        # Double check expiry
        if user.otp_expired is None or user.otp_expired < timezone.now():
            raise serializers.ValidationError("OTP has expired.")

        self.context['user'] = user
        return value


