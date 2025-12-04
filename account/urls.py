from django.urls import path
from .views import (SignupView,
    VerifyEmailOTPView,
    ResendOTPView,
    LoginView,
    ForgetPasswordView,
    ResetPasswordView, VerifyForgetPasswordOTPView
)

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-email-otp/', VerifyEmailOTPView.as_view(), name='verify_email_otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend_otp'),
    path('login/', LoginView.as_view(), name='login'),

    # Password reset
    path('forget-password/', ForgetPasswordView.as_view(), name='forget_password'),
    path('verify-forget-password-otp/', VerifyForgetPasswordOTPView.as_view(), name='verify_forget_password_otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),

    # User profile
    # path('profile/update/', UpdateProfileView.as_view(), name='update_profile'),
    # path('user/<int:user_id>/', SpecificUserView.as_view(), name='specific_user'),
    # path('delete-user/<int:user_id>/', DeleteUserView.as_view(), name='delete-user'),
]
