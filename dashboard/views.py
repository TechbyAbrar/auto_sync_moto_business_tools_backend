from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone
from datetime import date
import logging
from .serializers import DashboardStatsSerializer, UserListSerializer
from account.models import UserAuth
from unit.models import SellUnit, ScheduleService
from account.utils import success_response, error_response
from datetime import timedelta
from django.shortcuts import get_object_or_404
from .serializers import UserDetailSerializer

logger = logging.getLogger(__name__)

from rest_framework.pagination import PageNumberPagination

class DashboardUserPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    CACHE_TTL = 300
    CACHE_KEY = "dashboard_stats"

    def get(self, request):
        try:
            page = request.query_params.get("page", 1)
            page_size = request.query_params.get("page_size", 20)

            cache_key = f"{self.CACHE_KEY}_p{page}_s{page_size}"

            cached_data = cache.get(cache_key)
            if cached_data:
                return success_response(
                    message="Dashboard data fetched successfully (cached)",
                    data=cached_data,
                    status_code=status.HTTP_200_OK
                )

            # Build raw data
            raw_data = self._build_dashboard_data()

            # Paginate user list
            paginator = DashboardUserPagination()
            paginated_users = paginator.paginate_queryset(raw_data["users"], request)

            # Inject paginated data
            raw_data["users"] = paginated_users

            # Validate
            serializer = DashboardStatsSerializer(data=raw_data)
            serializer.is_valid(raise_exception=True)
            validated = serializer.data

            # META pagination
            validated["meta"] = {
                "pagination": {
                    "current_page": paginator.page.number,
                    "total_pages": paginator.page.paginator.num_pages,
                    "page_size": paginator.get_page_size(request),
                    "total_items": paginator.page.paginator.count,
                }
            }

            cache.set(cache_key, validated, self.CACHE_TTL)

            return success_response(
                message="Dashboard data fetched successfully",
                data=validated,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            logger.exception("Dashboard API error", extra={"exception": str(e)})
            return error_response(
                message="Failed to fetch dashboard data",
                errors={"detail": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                code="DASHBOARD_INTERNAL_ERROR"
            )

    # ⬇⬇⬇ MUST BE INSIDE THE CLASS ⬇⬇⬇
    def _build_dashboard_data(self):
        today = date.today()

        total_users = UserAuth.objects.filter(is_active=True).count()

        appointments_today = ScheduleService.objects.filter(
            appointment_date=today
        ).count()

        sales_today = SellUnit.objects.filter(
            created_at__date=today
        ).count()

        first_day_this_month = today.replace(day=1)
        first_day_last_month = (first_day_this_month - timedelta(days=1)).replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)

        current_month_appointments = ScheduleService.objects.filter(
            appointment_date__gte=first_day_this_month,
            appointment_date__lte=today
        ).count()

        last_month_appointments = ScheduleService.objects.filter(
            appointment_date__gte=first_day_last_month,
            appointment_date__lte=last_day_last_month
        ).count()

        users = UserAuth.objects.filter(is_active=True).values(
            "user_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "address",
            "dob",
            "zip_code"
        ).order_by("-created_at")

        return {
            "total_users": total_users,
            "appointments_today": appointments_today,
            "sales_today": sales_today,
            "current_month_appointments": current_month_appointments,
            "last_month_appointments": last_month_appointments,
            "users": list(users),  # will be paginated later
        }



# User Details View

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = get_object_or_404(
                UserAuth.objects.only(
                    "user_id",
                    "email",
                    "first_name",
                    "last_name",
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
                ),
                user_id=user_id,
            )

            serializer = UserDetailSerializer(user)

            return success_response(
                message="User fetched successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK,
            )

        except Exception as e:
            return error_response(
                message="Failed to fetch user information",
                errors={"detail": str(e)},
                code="USER_FETCH_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )