from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.cache import cache
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import django.db.models as models

from .models import ChatRoom, Message, invalidate_room_cache
from .serializers import ChatRoomSerializer, MessageSerializer
from .permissions import IsParticipantOrStaff
from rest_framework.pagination import PageNumberPagination

channel_layer = get_channel_layer()

class SmallPagination(PageNumberPagination):
    page_size = 20

class ListChatRoomsAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatRoomSerializer
    pagination_class = SmallPagination

    def get_queryset(self):
        user = self.request.user
        # return rooms where user is participant
        return ChatRoom.objects.filter(models.Q(user=user) | models.Q(staff=user)).select_related('user','staff')

class ListMessagesAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsParticipantOrStaff]
    serializer_class = MessageSerializer
    pagination_class = SmallPagination

    def get_queryset(self):
        room_id = self.kwargs['room_id']
        room = get_object_or_404(ChatRoom, pk=room_id)
        self.check_object_permissions(self.request, room)

        # try cache first for first pages
        page_num = int(self.request.query_params.get('page', 1))
        cache_key = f"chat:room:{room_id}:messages:page:{page_num}"
        cached = cache.get(cache_key)
        if cached:
            return cached  # NOTE: DRF expects queryset; We'll return queryset below if None (so better cache serialized pages)
        qs = room.messages.select_related('sender').all()
        return qs

    def list(self, request, *args, **kwargs):
        """
        We will try to cache serialized page payloads for efficiency.
        """
        room_id = self.kwargs['room_id']
        page_num = int(request.query_params.get('page', 1))
        cache_key = f"chat:room:{room_id}:messages:page:{page_num}"
        data = cache.get(cache_key)
        if data:
            return Response(data)

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True, context={'request': request})
        out = self.get_paginated_response(serializer.data).data
        cache.set(cache_key, out, timeout=30)  # short TTL, 30s (adjust as needed)
        return Response(out)

class SendMessageAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsParticipantOrStaff]
    serializer_class = MessageSerializer

    def perform_create(self, serializer):
        # ensure sender matches request.user
        with transaction.atomic():
            msg = serializer.save(sender=self.request.user)
            # Invalidate caches
            invalidate_room_cache(msg.room_id)
            # notify via channels to group 'chat_{room_id}'
            async_to_sync(channel_layer.group_send)(
                f"chat_{msg.room_id}",
                {
                    "type": "chat.message",
                    "message": MessageSerializer(msg, context={'request': self.request}).data
                }
            )
            return msg

    def create(self, request, *args, **kwargs):
        # extra validation: room exists and user is participant
        room = get_object_or_404(ChatRoom, pk=request.data.get('room'))
        self.check_object_permissions(request, room)
        return super().create(request, *args, **kwargs)
