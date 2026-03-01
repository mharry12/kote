from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminUser(BasePermission):
    """Allow access only to users with role='admin'."""

    message = 'Admin privileges required.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_admin_user()
        )


class IsOwnerOrAdmin(BasePermission):
    """Object-level: owner or admin can access."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_admin_user():
            return True
        return obj == request.user


class IsRegularUser(BasePermission):
    """Allow access only to regular (non-admin) users."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and not request.user.is_admin_user()
        )


class ReadOnly(BasePermission):
    """Allow safe (read-only) methods to anyone."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS