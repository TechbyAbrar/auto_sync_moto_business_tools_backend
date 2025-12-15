from django.contrib import admin
from .models import ChatRoom, Message


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "staff",
        "created_at",
        "updated_at",
    )
    list_filter = ("created_at", "updated_at")
    search_fields = ("user__email", "staff__email", "user__username", "staff__username")
    ordering = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user", "staff")

    def get_queryset(self, request):
        """
        Optimize admin queries by prefetching related messages
        """
        qs = super().get_queryset(request)
        return qs.select_related("user", "staff")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room",
        "sender",
        "short_text",
        "attachment_type",
        "created_at",
    )
    list_filter = ("attachment_type", "created_at")
    search_fields = (
        "text",
        "sender__email",
        "sender__username",
        "room__id",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    autocomplete_fields = ("room", "sender")
    filter_horizontal = ("read_by",)

    def short_text(self, obj):
        """
        Display a short preview of message text
        """
        if obj.text:
            return obj.text[:50]
        return "-"
    short_text.short_description = "Message Preview"

    def get_queryset(self, request):
        """
        Optimize admin queries
        """
        qs = super().get_queryset(request)
        return qs.select_related("room", "sender").prefetch_related("read_by")
