from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied


class IsAdminWithAccessCode(BasePermission):
    """
    Allows GET access only to admin users who supply a valid access code.

    Checks (in order):
      1. User must be authenticated via JWT Bearer token
      2. User role must be 'admin'
      3. Must provide the correct 8-char access_code via:
            - request body      { "access_code": "Ab3Xy7Qz" }
            - query param       ?access_code=Ab3Xy7Qz
            - request header    X-Access-Code: Ab3Xy7Qz
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            raise AuthenticationFailed("Authentication required.")

        if not user.is_admin_user():
            raise PermissionDenied("Admin privileges required.")

        access_code = (
            request.data.get("access_code")
            or request.query_params.get("access_code")
            or request.headers.get("X-Access-Code", "")
        ).strip()

        if not access_code:
            raise PermissionDenied("Access code is required.")

        if not user.verify_access_code(access_code):
            raise PermissionDenied("Invalid access code.")

        return True