from django.urls import path
from .views import (
    GetOrCreateRoomAPIView,
    ListChatRoomsAPIView,
    ListMessagesAPIView,
    SendMessageAPIView,
    MarkMessagesReadAPIView,
    ListStaffUsersAPIView,
    UnreadCountROOMAPIView,
    RoomUnreadCountAPIView,
    DeleteMessageAPIView,
)

urlpatterns = [
    # Room management
    path("rooms/create/", GetOrCreateRoomAPIView.as_view(), name="chat-create-room"),
    path("rooms/", ListChatRoomsAPIView.as_view(), name="chat-rooms"),
    path("rooms/<int:room_id>/unread-count/", RoomUnreadCountAPIView.as_view(), name="chat-room-unread"),
    
    # Messages
    path("rooms/<int:room_id>/messages/", ListMessagesAPIView.as_view(), name="chat-room-messages"),
    path("messages/send/", SendMessageAPIView.as_view(), name="chat-send-message"),
    path("messages/mark-read/", MarkMessagesReadAPIView.as_view(), name="chat-mark-read"),
    path("messages/<int:message_id>/delete/", DeleteMessageAPIView.as_view(), name="chat-delete-message"),
    
    # Utilities
    path("staff/", ListStaffUsersAPIView.as_view(), name="chat-staff-list"),
    path("unread-count/rooms/", UnreadCountROOMAPIView.as_view(), name="chat-unread-count"),
]