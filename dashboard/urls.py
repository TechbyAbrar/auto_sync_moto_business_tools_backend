from django.urls import path
from .views import DashboardView, UserDetailView

app_name = 'dashboard'

urlpatterns = [
    path('status/', DashboardView.as_view(), name='dashboard'),
    path("user/<int:user_id>/", UserDetailView.as_view(), name="user-detail"),
]



    

