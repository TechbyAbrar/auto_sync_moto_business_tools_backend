from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user info for chat"""
    class Meta:
        model = User
        fields = ('user_id', 'email', 'first_name', 'last_name', 'profile_pic')
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.ReadOnlyField(source='sender.user_id')
    sender_info = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            'id', 'room', 'sender_id', 'sender_info', 'text', 
            'attachment_url', 'attachment_type', 'created_at', 'is_read'
        )
        read_only_fields = ('id', 'sender_id', 'sender_info', 'created_at', 'attachment_type', 'is_read')

    def get_sender_info(self, obj):
        return {
            'user_id': obj.sender.user_id,
            'first_name': getattr(obj.sender, 'first_name', ''),
            'last_name': getattr(obj.sender, 'last_name', ''),
            'email': getattr(obj.sender, 'email', ''),
        }

    def get_attachment_url(self, obj):
        if obj.attachment:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.attachment.url) if request else obj.attachment.url
        return None
    
    def get_is_read(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.read_by.filter(user_id=request.user.user_id).exists()
        return False

    def validate(self, data):
        text = data.get('text')
        attachment = data.get('attachment')
        if not text and not attachment:
            raise serializers.ValidationError("Message must contain text or attachment.")
        if attachment and attachment.size > 15*1024*1024:
            raise serializers.ValidationError("Attachment too large. Max 15 MB.")
        return data


class ChatRoomSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ('id', 'user', 'staff', 'created_at', 'updated_at', 'last_message', 'other_user', 'unread_count')
        read_only_fields = fields

    def get_last_message(self, obj):
        m = obj.messages.select_related('sender').order_by('-created_at').first()
        if not m:
            return None
        return {
            'id': m.id,
            'text': m.text,
            'sender_id': m.sender.user_id,
            'created_at': m.created_at,
            'attachment_type': m.attachment_type,
        }

    def get_other_user(self, obj):
        request_user = self.context['request'].user
        other = obj.staff if request_user.user_id == obj.user_id else obj.user
        return {
            "user_id": other.user_id,
            "email": getattr(other, 'email', None),
            "first_name": getattr(other, 'first_name', ''),
            "last_name": getattr(other, 'last_name', ''),
            "profile_pic": other.profile_pic.url if other.profile_pic else None,
        }
    
    def get_unread_count(self, obj):
        request_user = self.context['request'].user
        return obj.get_unread_count(request_user)


class CreateRoomSerializer(serializers.Serializer):
    """Serializer for creating/getting a chat room"""
    other_user_id = serializers.IntegerField()
    
    def validate_other_user_id(self, value):
        request_user = self.context['request'].user
        
        # Can't chat with yourself
        if value == request_user.user_id:
            raise serializers.ValidationError("Cannot create chat room with yourself.")
        
        # Check if other user exists
        try:
            other_user = User.objects.get(user_id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        
        # Validate chat pairing (one must be staff)
        if request_user.is_staff and other_user.is_staff:
            raise serializers.ValidationError("Cannot create chat between two staff members.")
        if not request_user.is_staff and not other_user.is_staff:
            raise serializers.ValidationError("Cannot create chat between two regular users.")
        
        return value