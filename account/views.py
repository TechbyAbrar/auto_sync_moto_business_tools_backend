from django.db import transaction
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from .models import UserAuth
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
    VerifyForgetPasswordOTPSerializer, UserProfileUpdateSerializer
)
from .utils import generate_tokens_for_user, success_response, error_response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

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



# class VerifyEmailOTPView(APIView):
#     permission_classes = [AllowAny]

#     @transaction.atomic
#     def post(self, request):
#         serializer = VerifyEmailOTPSerializer(data=request.data)
#         if serializer.is_valid():
#             user = serializer.context["user"]
#             user.is_verified = True
#             user.save(update_fields=["is_verified"])  # minimal write

#             tokens = generate_tokens_for_user(user)
#             return success_response(
#                 "Email verified successfully",
#                 {"user_id": user.user_id, "email": user.email, "tokens": tokens},
#             )

#         return error_response("OTP verification failed", serializer.errors)

class VerifyEmailOTPView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = VerifyEmailOTPSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.context["user"]
            user.is_verified = True
            user.save(update_fields=["is_verified"])

            tokens = generate_tokens_for_user(user)

            return success_response(
                message="Email verified successfully",
                data={"access_token": tokens["access"]}
            )

        return error_response(
            message="OTP verification failed",
            data=serializer.errors,
            status_code=400
        )
    
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



class UserProfileUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self, user_id):
        # Use only() to load only required fields for update
        try:
            return UserAuth.objects.only(
                "user_id", "first_name", "last_name", "email",
                "username", "profile_pic", "dob", "phone", "address", "zip_code"
            ).get(user_id=user_id)
        except UserAuth.DoesNotExist:
            return None

    @transaction.atomic  # ensures atomic update
    def patch(self, request, user_id):
        user = self.get_object(user_id)
        if not user:
            return error_response(message="User not found.", status_code=404)

        # Only admin or the user themselves can update
        if request.user != user and not request.user.is_staff:
            return error_response(message="You do not have permission to update this user.", status_code=403)

        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            # Use update() to avoid extra save overhead for simple fields
            serializer.save()
            # Refresh from DB to get updated fields if needed
            user.refresh_from_db()
            return success_response(message="Profile updated successfully", data=serializer.data)

        return error_response(message="Validation errors", data=serializer.errors, status_code=400)
    
    
# account delete api
from django.shortcuts import get_object_or_404
from .permissions import IsSelfOrAdmin

class UserDeleteAPI(APIView):
    permission_classes = [IsAuthenticated, IsSelfOrAdmin]

    def delete(self, request):
        user_id = request.query_params.get("user_id")
        email = request.query_params.get("email")

        if not user_id and not email:
            return error_response(
                message="Either user_id or email must be provided.",
                status_code=400
            )

        if user_id:
            user = get_object_or_404(UserAuth, user_id=user_id)
        else:
            user = get_object_or_404(UserAuth, email=email)

        # Object-level permission check
        self.check_object_permissions(request, user)

        user.delete()

        return success_response(
            message="User account deleted successfully.",
            data={}
        )
        
        
class UserProfileAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user  # authenticated UserAuth instance
            serializer = UserSerializer(user)

            return success_response(
                message="User profile fetched successfully",
                data=serializer.data
            )

        except Exception as exc:
            return error_response(
                message="Failed to fetch user profile",
                data=str(exc),
                status_code=500
            )