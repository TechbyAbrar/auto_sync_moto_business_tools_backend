from django.db import transaction
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from .permissions import IsSuperUserOrReadOnly
from .serializers import (
    SignupSerializer,
    VerifyEmailOTPSerializer,
    ResendOTPSerializer,
    LoginSerializer,
    ForgetPasswordSerializer,
    ResetPasswordSerializer,
    UserSerializer,
    VerifyForgetPasswordOTPSerializer,
)
from .utils import generate_tokens_for_user, success_response, error_response

class SignupView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return success_response(
                "User registered successfully. Please verify your email.We have sent an OTP to your email.",
                {
                    "user_id": user.user_id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "username": user.username,
                },
                status_code=status.HTTP_201_CREATED,
            )
        return error_response("Signup failed", serializer.errors)



class VerifyEmailOTPView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = VerifyEmailOTPSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.context["user"]
            user.is_verified = True
            user.save(update_fields=["is_verified"])  # minimal write

            tokens = generate_tokens_for_user(user)
            return success_response(
                "Email verified successfully",
                {"user_id": user.user_id, "email": user.email, "tokens": tokens},
            )

        return error_response("OTP verification failed", serializer.errors)
    
class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return success_response(f"OTP resent to {user.email}")
        return error_response("Resend OTP failed", serializer.errors)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            tokens = generate_tokens_for_user(user)

            # Serialize user data
            user_data = UserSerializer(user).data
            user_data['tokens'] = tokens  # append JWT tokens

            return success_response(
                "Login successful",
                user_data
            )

        return error_response("Login failed", serializer.errors)


class ForgetPasswordView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = ForgetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return success_response(f"OTP sent to {user.email} for password reset.")
        return error_response("Forget password failed", serializer.errors)



class VerifyForgetPasswordOTPView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = VerifyForgetPasswordOTPSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.context['user']

            # Use the existing utility function to generate tokens
            tokens = generate_tokens_for_user(user)

            return success_response(
                f"OTP verified successfully for {user.email}",
                {"access_token": tokens["access"]}  # Only provide access token for reset
            )

        return error_response("OTP verification failed", serializer.errors)

class ResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]  # access token required

    @transaction.atomic
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data, context={"user": request.user})
        if serializer.is_valid():
            serializer.save()
            return success_response("Password reset successfully.")
        return error_response("Reset password failed", serializer.errors)

