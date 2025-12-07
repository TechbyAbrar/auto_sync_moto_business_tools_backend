from django.contrib import admin
from .models import RegisterUnit


@admin.register(RegisterUnit)
class RegisterUnitAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "vin",
        "brand",
        "model",
        "year",
        "registrar",
        "store_location",
        "created_at",
    )
    list_filter = ("brand", "year", "store_location", "registrar")
    search_fields = ("vin", "brand", "model", "registrar__email")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("registrar",)
    ordering = ("-created_at",)
