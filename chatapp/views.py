from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.cache import cache
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q, Prefetch, OuterRef, Subquery
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, EmptyPage

from .models import ChatRoom, Message, invalidate_room_cache, invalidate_unread_cache
from .serializers import (
    ChatRoomSerializer, 
    MessageSerializer, 
    CreateRoomSerializer,
    UserMinimalSerializer
)
from .permissions import IsParticipantOrStaff

User = get_user_model()
channel_layer = get_channel_layer()


class GetOrCreateRoomAPIView(APIView):
    """
    POST: Create or get existing chat room
    Body: {"other_user_id": 123}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateRoomSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        other_user_id = serializer.validated_data['other_user_id']
        current_user = request.user
        
        try:
            other_user = User.objects.get(user_id=other_user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Determine who is staff and who is user
        if current_user.is_staff:
            staff_user = current_user
            regular_user = other_user
        else:
            staff_user = other_user
            regular_user = current_user
        
        # Get or create room
        room, created = ChatRoom.objects.get_or_create(
            user=regular_user,
            staff=staff_user,
        )
        
        # Invalidate room list cache for both users
        if created:
            cache.delete(f"chat:rooms:user:{regular_user.user_id}")
            cache.delete(f"chat:rooms:user:{staff_user.user_id}")
        
        room_serializer = ChatRoomSerializer(room, context={'request': request})
        return Response(
            {
                "room": room_serializer.data,
                "created": created
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class ListChatRoomsAPIView(APIView):
    """
    GET: List all chat rooms for current user
    Query params: ?page=1&page_size=20
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        
        # Limit page_size
        page_size = min(page_size, 100)
        
        # Check cache only for first page
        if page == 1:
            cache_key = f"chat:rooms:user:{user.user_id}:page:{page}"
            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(cached_data, status=status.HTTP_200_OK)
        
        # Build queryset
        queryset = ChatRoom.objects.filter(
            Q(user=user) | Q(staff=user)
        ).select_related('user', 'staff').order_by('-updated_at')
        
        # Use Django Paginator safely
        paginator = Paginator(queryset, page_size)
        try:
            rooms_page = paginator.page(page)
        except EmptyPage:
            rooms_page = []

        # Serialize page object
        serializer = ChatRoomSerializer(rooms_page, many=True, context={'request': request})
        
        response_data = {
            "count": paginator.count,
            "next": page + 1 if rooms_page and rooms_page.has_next() else None,
            "previous": page - 1 if rooms_page and rooms_page.has_previous() else None,
            "results": serializer.data
        }

        # Cache only first page for 30 seconds
        if page == 1:
            cache.set(cache_key, response_data, timeout=30)

        return Response(response_data, status=status.HTTP_200_OK)



class ListMessagesAPIView(APIView):
    permission_classes = [IsAuthenticated, IsParticipantOrStaff]

    def get(self, request, room_id):
        user = request.user
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        
        # Limit page_size
        if page_size > 100:
            page_size = 100
        
        # Get room and check permissions
        room = get_object_or_404(ChatRoom, pk=room_id)
        
        # Check permission
        if not (user.is_staff or room.user_id == user.user_id or room.staff_id == user.user_id):
            return Response(
                {"error": "You do not have permission to view this room"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check cache
        cache_key = f"chat:room:{room_id}:messages:page:{page}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)
        
        # Get messages
        queryset = Message.objects.filter(
            room=room
        ).select_related('sender').prefetch_related('read_by').order_by('-created_at')
        
        # Paginate
        paginator = Paginator(queryset, page_size)
        
        try:
            messages_page = paginator.page(page)
        except EmptyPage:
            response_data = {
                "count": paginator.count,
                "next": None,
                "previous": None,
                "results": []
            }
            cache.set(cache_key, response_data, timeout=300)
            return Response(response_data, status=status.HTTP_200_OK)
        
        # Serialize
        serializer = MessageSerializer(messages_page, many=True, context={'request': request})
        
        # Build response
        next_page = page + 1 if messages_page.has_next() else None
        previous_page = page - 1 if messages_page.has_previous() else None
        
        response_data = {
            "count": paginator.count,
            "next": next_page,
            "previous": previous_page,
            "results": serializer.data
        }
        

        cache_timeout = 30 if page == 1 else 300
        cache.set(cache_key, response_data, timeout=cache_timeout)
        
        return Response(response_data, status=status.HTTP_200_OK)


class MarkMessagesReadAPIView(APIView):
    permission_classes = [IsAuthenticated, IsParticipantOrStaff]

    def post(self, request):
        room_id = request.data.get('room_id')
        
        if not room_id:
            return Response(
                {"error": "room_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get room
        room = get_object_or_404(ChatRoom, pk=room_id)
        user = request.user
        
        # Check permission
        if not (user.is_staff or room.user_id == user.user_id or room.staff_id == user.user_id):
            return Response(
                {"error": "You do not have permission to access this room"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Mark as read
        room.mark_as_read(user)
        
        # Notify other user via WebSocket
        async_to_sync(channel_layer.group_send)(
            f"chat_{room_id}",
            {
                "type": "messages.read",
                "user_id": user.user_id,
                "room_id": room_id
            }
        )
        
        return Response(
            {"status": "success", "message": "Messages marked as read"}, 
            status=status.HTTP_200_OK
        )


class SendMessageAPIView(APIView):
    permission_classes = [IsAuthenticated, IsParticipantOrStaff]

    def post(self, request):
        user = request.user
        room_id = request.data.get("room")

        if not room_id:
            return Response(
                {"error": "room field is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get room
        room = get_object_or_404(ChatRoom, pk=room_id)
        
        # Check permissions
        if not (user.is_staff or room.user_id == user.user_id or room.staff_id == user.user_id):
            return Response(
                {"error": "You do not have permission to send messages in this room"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate and save message
        with transaction.atomic():
            serializer = MessageSerializer(data=request.data, context={'request': request})
            
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            msg = serializer.save(sender=user)
            
            # Update room's updated_at
            room.save(update_fields=['updated_at'])
            
            # Invalidate cache
            invalidate_unread_cache(room_id)

            # Prepare message data for WebSocket
            message_data = MessageSerializer(msg, context={"request": request}).data

            # WebSocket broadcast
            async_to_sync(channel_layer.group_send)(
                f"chat_{msg.room_id}",
                {
                    "type": "chat.message",
                    "message": message_data
                }
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ListStaffUsersAPIView(APIView):
    """
    GET: List all staff users
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        
        # Limit page_size
        if page_size > 100:
            page_size = 100
        
        # Only regular users can see staff list
        if user.is_staff:
            return Response({
                "count": 0,
                "next": None,
                "previous": None,
                "results": []
            }, status=status.HTTP_200_OK)
        
        # Check cache
        cache_key = f"chat:staff_list:page:{page}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)
        
        # Get staff users
        queryset = User.objects.filter(
            is_staff=True, 
            is_active=True
        ).order_by('first_name')
        
        # Paginate
        paginator = Paginator(queryset, page_size)
        
        try:
            staff_page = paginator.page(page)
        except EmptyPage:
            return Response({
                "count": paginator.count,
                "next": None,
                "previous": None,
                "results": []
            }, status=status.HTTP_200_OK)
        
        # Serialize
        serializer = UserMinimalSerializer(staff_page, many=True, context={'request': request})
        
        # Build response
        next_page = page + 1 if staff_page.has_next() else None
        previous_page = page - 1 if staff_page.has_previous() else None
        
        response_data = {
            "count": paginator.count,
            "next": next_page,
            "previous": previous_page,
            "results": serializer.data
        }
        
        # Cache for 10 minutes
        cache.set(cache_key, response_data, timeout=600)
        
        return Response(response_data, status=status.HTTP_200_OK)


class UnreadCountROOMAPIView(APIView):
    """
    GET: Get total unread message count across all rooms
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Check cache
        cache_key = f"chat:total_unread:{user.user_id}"
        total_unread = cache.get(cache_key)
        
        if total_unread is None:
            # Get all user's rooms
            rooms = ChatRoom.objects.filter(Q(user=user) | Q(staff=user))
            
            # Calculate total unread
            total_unread = 0
            for room in rooms:
                total_unread += room.get_unread_count(user)
            
            # Cache for 1 minute
            cache.set(cache_key, total_unread, timeout=60)
        
        return Response(
            {"total_unread": total_unread}, 
            status=status.HTTP_200_OK
        )


class RoomUnreadCountAPIView(APIView):
    """
    GET: Get unread message count for a specific room
    """
    permission_classes = [IsAuthenticated, IsParticipantOrStaff]

    def get(self, request, room_id):
        user = request.user
        
        # Get room
        room = get_object_or_404(ChatRoom, pk=room_id)
        
        # Check permission
        if not (user.is_staff or room.user_id == user.user_id or room.staff_id == user.user_id):
            return Response(
                {"error": "You do not have permission to access this room"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get unread count (cached inside the method)
        unread_count = room.get_unread_count(user)
        
        return Response(
            {
                "room_id": room_id,
                "unread_count": unread_count
            }, 
            status=status.HTTP_200_OK
        )


class DeleteMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, message_id):
        user = request.user
        
        # Get message
        message = get_object_or_404(Message, pk=message_id)
        
        # Check if user is the sender
        if message.sender_id != user.user_id:
            return Response(
                {"error": "You can only delete your own messages"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        room_id = message.room_id
        
        # Delete message
        message.delete()
        
        # Notify via WebSocket
        async_to_sync(channel_layer.group_send)(
            f"chat_{room_id}",
            {
                "type": "message.deleted",
                "message_id": message_id,
                "room_id": room_id
            }
        )
        
        return Response(
            {"status": "success", "message": "Message deleted"},
            status=status.HTTP_200_OK
        )