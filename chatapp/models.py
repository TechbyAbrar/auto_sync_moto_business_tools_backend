from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.core.cache import cache
from django.urls import reverse

User = settings.AUTH_USER_MODEL

class ChatRoom(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, related_name="chatrooms_as_user", on_delete=models.CASCADE)
    staff = models.ForeignKey(User, related_name="chatrooms_as_staff", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("user", "staff"),)
        indexes = [
            models.Index(fields=["user", "staff"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"room:{self.id} ({self.user_id} <-> {self.staff_id})"

class Message(models.Model):
    ATTACHMENT_NONE = 'none'
    ATTACHMENT_IMAGE = 'image'
    ATTACHMENT_VIDEO = 'video'
    ATTACHMENT_CHOICES = [
        (ATTACHMENT_IMAGE, 'image'),
        (ATTACHMENT_VIDEO, 'video'),
    ]

    id = models.AutoField(primary_key=True)
    room = models.ForeignKey(ChatRoom, related_name="messages", on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name="sent_messages", on_delete=models.CASCADE)
    text = models.TextField(blank=True, null=True)
    attachment = models.FileField(
        upload_to='chat/attachments/%Y/%m/%d/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg','jpeg','png','gif','mp4','mov','webm'])]
    )
    attachment_type = models.CharField(max_length=10, choices=ATTACHMENT_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(User, related_name="read_messages", blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['room', 'created_at']),
            models.Index(fields=['sender']),
        ]

    def mark_read(self, user):
        self.read_by.add(user)
        # Invalidate unread cache for user
        cache_key = f"chat:unread_count:{user.pk}"
        cache.delete(cache_key)

    def save(self, *args, **kwargs):
        # infer attachment type
        if self.attachment:
            lower = (self.attachment.name or "").lower()
            if lower.endswith(('.mp4', '.mov', '.webm')):
                self.attachment_type = self.ATTACHMENT_VIDEO
            else:
                self.attachment_type = self.ATTACHMENT_IMAGE
        return super().save(*args, **kwargs)

# Helper cache invalidation function (could be moved to signals or service layer)
def invalidate_room_cache(room_id):
    # pattern-based deletion; if you use Redis directly you can do keys pattern.
    # Simple approach: delete known keys (if you structured them deterministically)
    prefix = f"chat:room:{room_id}:messages:page:"
    # if your cache backend supports iterating keys (redis), you can delete exact keys used.
    # We'll delete common keys for first N pages to be safe:
    for p in range(1, 6):  # first 5 pages
        cache.delete(f"{prefix}{p}")
    # also invalidate last-message summary
    cache.delete(f"chat:room:{room_id}:last_message")
