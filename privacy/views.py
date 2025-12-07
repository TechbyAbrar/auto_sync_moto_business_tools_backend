# views.py
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db import transaction

from .models import (
    PrivacyPolicy, AboutUs, TermsConditions, SubmitQuery
)
from .serializers import (
    PrivacyPolicySerializer, AboutUsSerializer, TermsConditionsSerializer,
    SubmitQuerySerializer
)
from account.permissions import IsSuperUserOrReadOnly
from account.utils import success_response, error_response


# -------------------- Single Object Base Logic -------------------- #
class SingleObjectViewMixin:
    """Always return the first object in the queryset."""
    def get_object(self):
        return self.queryset.first()


class BaseSingleObjectView(SingleObjectViewMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [IsSuperUserOrReadOnly]

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return error_response("No content found.", status_code=404)

        serializer = self.get_serializer(instance)
        return success_response(
            message="Content retrieved successfully.",
            data=serializer.data,
        )

    @transaction.atomic
    def put(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer = (
            self.get_serializer(instance, data=request.data)
            if instance
            else self.get_serializer(data=request.data)
        )

        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=400,
            )

        serializer.save()
        return success_response(
            message="Content updated successfully." if instance else "Content created successfully.",
            data=serializer.data,
            status_code=200 if instance else 201,
        )

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer = (
            self.get_serializer(instance, data=request.data, partial=True)
            if instance
            else self.get_serializer(data=request.data, partial=True)
        )

        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=400,
            )

        serializer.save()
        return success_response(
            message="Content partially updated successfully." if instance else "Content created successfully.",
            data=serializer.data,
            status_code=200 if instance else 201,
        )


# -------------------- Views for Static Pages -------------------- #
class PrivacyPolicyView(BaseSingleObjectView):
    queryset = PrivacyPolicy.objects.all()
    serializer_class = PrivacyPolicySerializer


class AboutUsView(BaseSingleObjectView):
    queryset = AboutUs.objects.all()
    serializer_class = AboutUsSerializer


class TermsConditionsView(BaseSingleObjectView):
    queryset = TermsConditions.objects.all()
    serializer_class = TermsConditionsSerializer


# -------------------- Submit Query Views -------------------- #
class SubmitQueryView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SubmitQuerySerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        serializer.save()
        return success_response(
            message="User query submitted successfully!",
            data=serializer.data,
            status_code=201,
        )

    def get(self, request):
        queries = SubmitQuery.objects.only(
            "id", "name", "email", "message", "created_at"
        )

        serializer = SubmitQuerySerializer(queries, many=True)

        return success_response(
            message="All queries retrieved successfully.",
            data=serializer.data,
        )


class SubmitQueryDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            query = SubmitQuery.objects.only(
                "id", "name", "email", "message", "created_at"
            ).get(pk=pk)
        except SubmitQuery.DoesNotExist:
            return error_response(
                message="Query not found.",
                status_code=404,
            )

        serializer = SubmitQuerySerializer(query)
        return success_response(
            message="Query retrieved successfully.",
            data=serializer.data,
        )
