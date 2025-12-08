import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken
from django.conf import settings
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import DecodeError, ExpiredSignatureError
from asgiref.sync import sync_to_async
from .models import ChatRoom, Message, invalidate_room_cache
from django.db import transaction

User = get_user_model()

# helper to get user from token
@database_sync_to_async
def get_user_from_token(token):
    try:
        # validate token
        UntypedToken(token)
        # decode manually to get user id
        import jwt
        from django.conf import settings
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = data.get("user_id")
        return User.objects.get(pk=user_id)
    except Exception:
        return None

@database_sync_to_async
def save_message(room_id, sender, text=None, attachment=None):
    room = ChatRoom.objects.get(pk=room_id)
    with transaction.atomic():
        msg = Message.objects.create(room=room, sender=sender, text=text, attachment=attachment)
    # invalidate caches
    invalidate_room_cache(room_id)
    return msg

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        # Authenticate
        token = self.scope['query_string'].decode().split("token=")[-1] if b"token=" in self.scope['query_string'] else None
        self.user = None
        if token:
            self.user = await get_user_from_token(token)
        if not self.user or not self.user.is_active:
            await self.close()
            return

        self.room_id = self.scope['url_route']['kwargs']['room_id']
        # Check permissions: is participant?
        room = await database_sync_to_async(ChatRoom.objects.filter(pk=self.room_id).first)()
        if not room:
            await self.close()
            return
        if not (self.user.is_staff or room.user_id == self.user.pk or room.staff_id == self.user.pk):
            await self.close()
            return

        self.group_name = f"chat_{self.room_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        """
        Expected JSON:
        { "action": "send", "text": "hello" }
        For attachments via WS you may use base64 (not recommended). Prefer REST upload endpoint.
        """
        action = content.get('action')
        if action == 'send':
            text = content.get('text', '').strip()
            if not text and not content.get('attachment'):
                await self.send_json({"error":"text or attachment required"}, status=400)
                return
            # Save message in DB
            msg = await save_message(self.room_id, self.user, text=text or None)
            # Broadcast to group
            serialized = {
                "id": msg.id,
                "room": msg.room_id,
                "sender_id": msg.sender_id,
                "text": msg.text,
                "attachment_url": None,
                "attachment_type": None,
                "created_at": msg.created_at.isoformat()
            }
            await self.channel_layer.group_send(self.group_name, {
                "type": "chat.message",
                "message": serialized
            })

    async def chat_message(self, event):
        # send the message JSON to WebSocket
        await self.send_json({
            "type": "message",
            "message": event["message"]
        })
