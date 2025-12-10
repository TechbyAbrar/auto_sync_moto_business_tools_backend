from rest_framework import serializers
from .models import ChatRoom, Message
from django.conf import settings
from django.core.files.images import get_image_dimensions

class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.ReadOnlyField(source='sender.pk')
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ('id','room','sender_id','text','attachment_url','attachment_type','created_at')
        read_only_fields = ('id','sender_id','created_at','attachment_type')

    def get_attachment_url(self, obj):
        if obj.attachment:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.attachment.url) if request else obj.attachment.url
        return None

    def validate(self, data):
        text = data.get('text')
        attachment = data.get('attachment') if 'attachment' in data else None
        if not text and not attachment:
            raise serializers.ValidationError("Message must contain text or attachment.")
        # optionally validate file size
        if attachment:
            max_mb = 15
            if attachment.size > max_mb * 1024 * 1024:
                raise serializers.ValidationError(f"Attachment too large. Max {max_mb} MB.")
        return data

class ChatRoomSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ('id', 'user', 'staff', 'created_at', 'last_message', 'other_user')

    def get_last_message(self, obj):
        m = obj.messages.order_by('-created_at').first()
        if not m:
            return None
        return MessageSerializer(m, context=self.context).data

    def get_other_user(self, obj):
        request_user = self.context['request'].user
        other = obj.staff if request_user.pk == obj.user_id else obj.user
        return {
            "id": other.pk,
            "email": getattr(other, 'email', None),
            "first_name": getattr(other, 'first_name', '')
        }
