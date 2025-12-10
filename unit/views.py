import logging
from django.db import transaction
from django.core.cache import cache
from django.shortcuts import get_object_or_404

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import IsAuthenticated

from .models import RegisterUnit, ScheduleService, SellUnit
from .serializers import RegisterUnitSerializer, ScheduleServiceSerializer, SellUnitSerializer
from account.utils import success_response, error_response

logger = logging.getLogger(__name__)

CACHE_KEY = "registerunit_list"
CACHE_TIMEOUT = 60 * 5  # 5 minutes



# -------------------
# Create API
# -------------------
class RegisterUnitCreateAPIView(generics.CreateAPIView):
    serializer_class = RegisterUnitSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            # Invalidate cache
            cache.delete(CACHE_KEY)

            logger.info("RegisterUnit created", extra={"unit_id": instance.id, "user": request.user.user_id})
            return success_response(
                message="Register unit created successfully",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )

        except ValidationError as exc:
            return error_response(
                message="Validation failed",
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )


# -------------------
# List API
# -------------------
class RegisterUnitListAPIView(generics.ListAPIView):
    serializer_class = RegisterUnitSerializer
    pagination_class = None  # Add pagination if needed

    def get_queryset(self):
        cached = cache.get(CACHE_KEY)
        if cached:
            return cached
        qs = RegisterUnit.objects.select_related("registrar").all().order_by("-created_at")
        cache.set(CACHE_KEY, qs, CACHE_TIMEOUT)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        return success_response(
            message="Register units fetched successfully",
            data={"results": serializer.data}
        )


# -------------------
# Retrieve API
# -------------------
class RegisterUnitRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = RegisterUnitSerializer
    queryset = RegisterUnit.objects.select_related("registrar").all()
    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            return success_response(
                message="Register unit retrieved successfully",
                data=serializer.data
            )

        except NotFound:
            return error_response(
                message="Register unit not found",
                status_code=status.HTTP_404_NOT_FOUND
            )


# -------------------
# Update API (PATCH)
# -------------------
class RegisterUnitUpdateAPIView(generics.UpdateAPIView):
    serializer_class = RegisterUnitSerializer
    queryset = RegisterUnit.objects.all()
    lookup_field = "id"

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            cache.delete(CACHE_KEY)

            logger.info("RegisterUnit updated", extra={"unit_id": instance.id, "user": request.user.user_id})

            return success_response(
                message="Register unit updated successfully",
                data=serializer.data
            )

        except ValidationError as exc:
            return error_response(
                message="Validation failed",
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        except NotFound:
            return error_response(
                message="Register unit not found",
                status_code=status.HTTP_404_NOT_FOUND
            )


# -------------------
# Delete API
# -------------------
class RegisterUnitDeleteAPIView(generics.DestroyAPIView):
    serializer_class = RegisterUnitSerializer
    queryset = RegisterUnit.objects.all()
    lookup_field = "id"

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance_id = instance.id
            instance.delete()

            cache.delete(CACHE_KEY)

            logger.info("RegisterUnit deleted", extra={"unit_id": instance_id, "user": request.user.user_id})

            return success_response(
                message="Register unit deleted successfully",
                data={},
                status_code=status.HTTP_200_OK
            )

        except NotFound:
            return error_response(
                message="Register unit not found",
                status_code=status.HTTP_404_NOT_FOUND
            )





# schedule service views

class ScheduleServiceListCreateAPIView(APIView, PageNumberPagination):
    page_size = 10

    def get(self, request):
        cache_key = "all_services_page_" + str(request.query_params.get("page", 1))
        cached_data = cache.get(cache_key)
        if cached_data:
            return success_response(data=cached_data)

        services = ScheduleService.objects.select_related("unit").all()
        results = self.paginate_queryset(services, request, view=self)
        serializer = ScheduleServiceSerializer(results, many=True)
        cache.set(cache_key, serializer.data, CACHE_TIMEOUT)
        return self.get_paginated_response(success_response(data=serializer.data).data)

    @transaction.atomic
    def post(self, request):
        serializer = ScheduleServiceSerializer(data=request.data)
        if serializer.is_valid():
            service = serializer.save()
            cache.clear()
            logger.info(f"Created ScheduleService ID={service.id}")
            return success_response(data=serializer.data, message="Service created", status_code=status.HTTP_201_CREATED)
        logger.error(f"ScheduleService creation failed: {serializer.errors}")
        return error_response(errors=serializer.errors, message="Service creation failed", status_code=status.HTTP_400_BAD_REQUEST)


class ScheduleServiceDetailAPIView(APIView):
    """Retrieve, update a single ScheduleService"""

    def get_object(self, pk):
        return get_object_or_404(ScheduleService, pk=pk)

    def get(self, request, pk):
        service = self.get_object(pk)
        serializer = ScheduleServiceSerializer(service)
        return success_response(data=serializer.data)

    @transaction.atomic
    def put(self, request, pk):
        service = self.get_object(pk)
        serializer = ScheduleServiceSerializer(service, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            cache.clear()
            logger.info(f"Updated ScheduleService ID={service.id}")
            return success_response(data=serializer.data, message="Service updated")
        logger.error(f"ScheduleService update failed: {serializer.errors}")
        return error_response(errors=serializer.errors, message="Service update failed", status_code=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def patch(self, request, pk):
        """Partial update"""
        service = self.get_object(pk)
        serializer = ScheduleServiceSerializer(service, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            cache.clear()
            logger.info(f"Partially updated ScheduleService ID={service.id}")
            return success_response(data=serializer.data, message="Service partially updated")
        logger.error(f"ScheduleService partial update failed: {serializer.errors}")
        return error_response(errors=serializer.errors, message="Service partial update failed", status_code=status.HTTP_400_BAD_REQUEST)



# sell unit views

SELL_UNIT_CACHE_KEY = "sell_units_list"
SELL_UNIT_CACHE_TIMEOUT = 60 * 5  # 5 minutes

class SellUnitCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = SellUnitSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        sell_unit = serializer.save(seller=request.user)
        logger.info(f"SellUnit created with ID: {sell_unit.id} by User: {request.user.user_id}")

        cache.delete(SELL_UNIT_CACHE_KEY)

        return success_response(
            message="Unit listed for sale successfully.",
            data=SellUnitSerializer(sell_unit).data,
            status_code=status.HTTP_201_CREATED
        )

    def get(self, request):
        # Try to get cached data
        cached_data = cache.get(SELL_UNIT_CACHE_KEY)

        if cached_data:
            return success_response(
                message="Sell units retrieved successfully (cached).",
                data=cached_data,
                status_code=status.HTTP_200_OK
            )

        # Not cached → fetch from DB
        queryset = SellUnit.objects.select_related("unit", "seller").order_by("-created_at")
        serializer = SellUnitSerializer(queryset, many=True)

        # Store in Redis
        cache.set(SELL_UNIT_CACHE_KEY, serializer.data, SELL_UNIT_CACHE_TIMEOUT)

        return success_response(
            message="Sell units retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

class SellUnitDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            sell_unit = SellUnit.objects.select_related("unit", "seller").get(pk=pk)
        except SellUnit.DoesNotExist:
            return error_response(
                message="Sell unit not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = SellUnitSerializer(sell_unit)
        return success_response(
            message="Sell unit retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
