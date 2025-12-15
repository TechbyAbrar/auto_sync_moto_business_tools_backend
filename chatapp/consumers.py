from urllib.parse import parse_qs
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import ChatRoom, Message, invalidate_room_cache

logger = logging.getLogger("chatapp")
User = get_user_model()


@database_sync_to_async
def get_user_from_token(token: str):
    """Validate JWT token and return user"""
    try:
        validated = UntypedToken(token)
        user_id = validated.payload.get("user_id")
        return User.objects.only(
            "user_id", "is_active", "is_staff", "first_name", "last_name", "email"
        ).get(user_id=user_id)
    except (TokenError, User.DoesNotExist):
        return None


@database_sync_to_async
def get_room(room_id: int):
    """Get chat room by ID"""
    try:
        return ChatRoom.objects.only(
            "id", "user_id", "staff_id"
        ).get(id=room_id)
    except ChatRoom.DoesNotExist:
        return None


@database_sync_to_async
def save_message(room_id, sender, text=None):
    """Save message to database"""
    msg = Message.objects.create(
        room_id=room_id,
        sender=sender,
        text=text
    )
    # Auto mark as read by sender
    msg.read_by.add(sender)
    
    # Update room timestamp
    ChatRoom.objects.filter(id=room_id).update()
    
    invalidate_room_cache(room_id)
    return msg


@database_sync_to_async
def mark_room_as_read(room_id, user):
    """Mark all messages in room as read for user"""
    try:
        room = ChatRoom.objects.get(id=room_id)
        room.mark_as_read(user)
        return True
    except ChatRoom.DoesNotExist:
        return False


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time chat
    
    Connection: ws://domain/ws/chat/<room_id>/?token=<jwt_token>
    
    Receive events:
    - {"action": "send", "text": "message"}
    - {"action": "mark_read"}
    - {"action": "typing", "is_typing": true}
    
    Send events:
    - {"type": "message", "message": {...}}
    - {"type": "read", "user_id": 123}
    - {"type": "typing", "user_id": 123, "is_typing": true}
    - {"type": "error", "error": "..."}
    """

    async def connect(self):
        """Handle WebSocket connection"""
        query_params = parse_qs(
            self.scope.get("query_string", b"").decode()
        )
        token = query_params.get("token", [None])[0]

        if not token:
            logger.warning("WS rejected: missing token")
            await self.close(code=4001)
            return

        # Authenticate user
        self.user = await get_user_from_token(token)
        if not self.user or not self.user.is_active:
            logger.warning("WS rejected: invalid user")
            await self.close(code=4003)
            return

        # Get room
        self.room_id = int(self.scope["url_route"]["kwargs"]["room_id"])
        room = await get_room(self.room_id)
        
        if not room:
            logger.warning(f"WS rejected: room {self.room_id} not found")
            await self.close(code=4004)
            return

        # Check permissions
        if not (
            self.user.is_staff
            or room.user_id == self.user.user_id
            or room.staff_id == self.user.user_id
        ):
            logger.warning(f"WS rejected: user {self.user.user_id} no permission for room {self.room_id}")
            await self.close(code=4003)
            return

        # Join room group
        self.group_name = f"chat_{self.room_id}"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

        logger.info(
            f"WS connected: user={self.user.user_id} room={self.room_id}"
        )
        
        # Notify others that user is online
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "user.online",
                "user_id": self.user.user_id,
            }
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'group_name'):
            # Notify others that user is offline
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "user.offline",
                    "user_id": self.user.user_id,
                }
            )
            
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            logger.info(f"WS disconnected: user={self.user.user_id} room={self.room_id}")

    async def receive_json(self, content):
        """Handle incoming WebSocket messages"""
        action = content.get("action")

        if action == "send":
            # Send text message
            text = (content.get("text") or "").strip()
            if not text:
                await self.send_json({"type": "error", "error": "Message text required"})
                return

            # Save message
            msg = await save_message(
                room_id=self.room_id,
                sender=self.user,
                text=text
            )

            # Broadcast to all in room
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat.message",
                    "message": {
                        "id": msg.id,
                        "room": msg.room_id,
                        "sender_id": msg.sender_id,
                        "sender_info": {
                            "user_id": self.user.user_id,
                            "first_name": self.user.first_name or "",
                            "last_name": self.user.last_name or "",
                            "email": self.user.email or "",
                        },
                        "text": msg.text,
                        "attachment_url": None,
                        "attachment_type": "none",
                        "created_at": msg.created_at.isoformat(),
                        "is_read": False,
                    }
                }
            )

        elif action == "mark_read":
            # Mark all messages as read
            success = await mark_room_as_read(self.room_id, self.user)
            if success:
                # Notify others
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "messages.read",
                        "user_id": self.user.user_id,
                        "room_id": self.room_id
                    }
                )

        elif action == "typing":
            # Typing indicator
            is_typing = content.get("is_typing", False)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "user.typing",
                    "user_id": self.user.user_id,
                    "is_typing": is_typing
                }
            )

        else:
            await self.send_json({"type": "error", "error": "Unknown action"})

    # Group message handlers
    async def chat_message(self, event):
        """Send message to WebSocket"""
        await self.send_json({
            "type": "message",
            "message": event["message"]
        })

    async def messages_read(self, event):
        """Notify that messages were read"""
        await self.send_json({
            "type": "read",
            "user_id": event["user_id"],
            "room_id": event["room_id"]
        })

    async def user_typing(self, event):
        """Send typing indicator"""
        # Don't send typing event back to the user who is typing
        if event["user_id"] != self.user.user_id:
            await self.send_json({
                "type": "typing",
                "user_id": event["user_id"],
                "is_typing": event["is_typing"]
            })

    async def user_online(self, event):
        """Notify that user came online"""
        if event["user_id"] != self.user.user_id:
            await self.send_json({
                "type": "online",
                "user_id": event["user_id"]
            })

    async def user_offline(self, event):
        """Notify that user went offline"""
        if event["user_id"] != self.user.user_id:
            await self.send_json({
                "type": "offline",
                "user_id": event["user_id"]
            })