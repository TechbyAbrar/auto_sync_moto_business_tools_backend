from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

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
            models.Index(fields=["-updated_at"]),
        ]

    def __str__(self):
        return f"room:{self.id} ({self.user_id} <-> {self.staff_id})"
    
    def get_unread_count(self, for_user):
        """Get unread message count for specific user with caching"""
        cache_key = f"chat:room:{self.id}:unread:{for_user.user_id}"
        count = cache.get(cache_key)
        
        if count is None:
            count = self.messages.exclude(
                read_by=for_user
            ).exclude(
                sender=for_user
            ).count()
            cache.set(cache_key, count, timeout=60)  # Cache for 1 minute
        
        return count
    
    def mark_as_read(self, for_user):
        messages = self.messages.exclude(read_by=for_user).exclude(sender=for_user)
        for msg in messages:
            msg.read_by.add(for_user)
        
        # Invalidate cache after marking as read
        invalidate_room_cache(self.id)
        invalidate_unread_cache(self.id, for_user.user_id)


class Message(models.Model):
    ATTACHMENT_NONE = 'none'
    ATTACHMENT_IMAGE = 'image'
    ATTACHMENT_CHOICES = [
        (ATTACHMENT_IMAGE, 'image'),
    ]

    id = models.AutoField(primary_key=True)
    room = models.ForeignKey(ChatRoom, related_name="messages", on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name="sent_messages", on_delete=models.CASCADE)
    text = models.TextField(blank=True, null=True)
    attachment = models.ImageField(
        upload_to='chat/attachments/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg','jpeg','png','gif','webp'])]
    )
    attachment_type = models.CharField(max_length=10, choices=ATTACHMENT_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_by = models.ManyToManyField(User, related_name="read_messages", blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['room', 'created_at']),
            models.Index(fields=['sender']),
        ]

    def save(self, *args, **kwargs):
        if self.attachment:
            self.attachment_type = self.ATTACHMENT_IMAGE
        else:
            self.attachment_type = self.ATTACHMENT_NONE
        is_new = self.pk is None
        result = super().save(*args, **kwargs)
        
        # Auto mark as read by sender
        if is_new:
            self.read_by.add(self.sender)
        
        return result


# Cache invalidation functions
def invalidate_room_cache(room_id):
    """Invalidate all cache related to a room"""
    # Invalidate message pages
    for page in range(1, 20):  # Support up to 20 pages
        cache.delete(f"chat:room:{room_id}:messages:page:{page}")
    
    # Invalidate room list cache for both participants
    try:
        room = ChatRoom.objects.get(id=room_id)
        cache.delete(f"chat:rooms:user:{room.user_id}")
        cache.delete(f"chat:rooms:user:{room.staff_id}")
    except ChatRoom.DoesNotExist:
        pass


def invalidate_unread_cache(room_id, user_id=None):
    """Invalidate unread count cache"""
    if user_id:
        cache.delete(f"chat:room:{room_id}:unread:{user_id}")
        cache.delete(f"chat:total_unread:{user_id}")
    else:
        # Invalidate for both users in the room
        try:
            room = ChatRoom.objects.get(id=room_id)
            cache.delete(f"chat:room:{room_id}:unread:{room.user_id}")
            cache.delete(f"chat:room:{room_id}:unread:{room.staff_id}")
            cache.delete(f"chat:total_unread:{room.user_id}")
            cache.delete(f"chat:total_unread:{room.staff_id}")
        except ChatRoom.DoesNotExist:
            pass


# Signals to auto-invalidate cache
@receiver(post_save, sender=Message)
def message_saved(sender, instance, created, **kwargs):
    """Invalidate cache when message is created or updated"""
    if created:
        invalidate_room_cache(instance.room_id)
        invalidate_unread_cache(instance.room_id)


@receiver(post_delete, sender=Message)
def message_deleted(sender, instance, **kwargs):
    """Invalidate cache when message is deleted"""
    invalidate_room_cache(instance.room_id)
    invalidate_unread_cache(instance.room_id)


@receiver(post_save, sender=ChatRoom)
def room_saved(sender, instance, created, **kwargs):
    """Invalidate room list cache when room is created or updated"""
    cache.delete(f"chat:rooms:user:{instance.user_id}")
    cache.delete(f"chat:rooms:user:{instance.staff_id}")