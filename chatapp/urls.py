from django.urls import path
from .views import ListChatRoomsAPIView, ListMessagesAPIView, SendMessageAPIView

urlpatterns = [
    path("rooms/", ListChatRoomsAPIView.as_view(), name="chat-rooms"),
    path("rooms/<int:room_id>/messages/", ListMessagesAPIView.as_view(), name="chat-room-messages"),
    path("messages/send/", SendMessageAPIView.as_view(), name="chat-send-message"),
]
