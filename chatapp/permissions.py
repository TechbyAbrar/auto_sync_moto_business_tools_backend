from rest_framework.permissions import BasePermission

class IsParticipantOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
            return True
        # if obj is ChatRoom
        if hasattr(obj, 'user_id') and hasattr(obj, 'staff_id'):
            return obj.user_id == user.pk or obj.staff_id == user.pk
        # if obj is Message
        if hasattr(obj, 'room'):
            room = obj.room
            return room.user_id == user.pk or room.staff_id == user.pk
        return False