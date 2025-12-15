from rest_framework.permissions import BasePermission

class IsParticipantOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff or getattr(user, 'is_superuser', False):
            return True
        if hasattr(obj, 'user_id') and hasattr(obj, 'staff_id'):
            return obj.user_id == user.user_id or obj.staff_id == user.user_id
        if hasattr(obj, 'room'):
            return obj.room.user_id == user.user_id or obj.room.staff_id == user.user_id
        return False