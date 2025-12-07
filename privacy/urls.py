# app_name/urls.py
from django.urls import path
from .views import (
    PrivacyPolicyView,
    AboutUsView,
    TermsConditionsView,
    SubmitQueryView,
    SubmitQueryDetailView,
)

urlpatterns = [
    # ---- Static Content Pages (Single Object CRUD) ----
    path("privacy-policy/", PrivacyPolicyView.as_view(), name="privacy-policy"),
    path("about-us/", AboutUsView.as_view(), name="about-us"),
    path("terms-conditions/", TermsConditionsView.as_view(), name="terms-conditions"),

    # ---- Submit Query (Contact Form) ----
    path("queries/", SubmitQueryView.as_view(), name="submit-query"),
    path("queries/<int:pk>/", SubmitQueryDetailView.as_view(), name="query-detail"),
]
