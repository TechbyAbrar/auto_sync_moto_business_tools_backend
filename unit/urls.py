from django.urls import path
from .views import (
    RegisterUnitCreateAPIView,
    RegisterUnitListAPIView,
    RegisterUnitRetrieveAPIView,
    RegisterUnitUpdateAPIView,
    RegisterUnitDeleteAPIView, ScheduleServiceListCreateAPIView, ScheduleServiceDetailAPIView
)

urlpatterns = [
    path('register-units/', RegisterUnitListAPIView.as_view(), name='registerunit-list'),
    path('register-units/create/', RegisterUnitCreateAPIView.as_view(), name='registerunit-create'),
    path('register-units/<int:id>/', RegisterUnitRetrieveAPIView.as_view(), name='registerunit-detail'),
    path('register-units/<int:id>/update/', RegisterUnitUpdateAPIView.as_view(), name='registerunit-update'),
    path('register-units/<int:id>/delete/', RegisterUnitDeleteAPIView.as_view(), name='registerunit-delete'),
    #services
    path("services/", ScheduleServiceListCreateAPIView.as_view(), name="service-list-create"),
    path("services/<int:pk>/", ScheduleServiceDetailAPIView.as_view(), name="service-detail"),
]
