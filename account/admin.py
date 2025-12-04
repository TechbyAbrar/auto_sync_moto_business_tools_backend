# account/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserAuth

@admin.register(UserAuth)
class UserAuthAdmin(BaseUserAdmin):
    # Fields to display in list view
    list_display = ('email', 'first_name', 'last_name', 'is_verified', 'is_staff', 'is_superuser', 'created_at')
    list_filter = ('is_verified', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'username', 'phone')
    ordering = ('-created_at',)
    
    # Fields used for editing user in admin
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'username', 'profile_pic', 'profile_pic_url', 'phone', 'address', 'zip_code', 'dob')}),
        ('Permissions', {'fields': ('is_verified', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('OTP', {'fields': ('otp', 'otp_expired')}),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'is_staff', 'is_superuser', 'is_verified'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
