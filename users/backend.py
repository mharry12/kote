from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend(ModelBackend):
    """
    Authenticate using email instead of username.
    Falls through to the default backend automatically.
    """

    def authenticate(self, request, email=None, password=None, **kwargs):
        # Also accept 'username' kwarg (Django admin passes it as username)
        email = email or kwargs.get('username')
        if not email or not password:
            return None
        try:
            user = User.objects.get(email=email.lower().strip())
        except User.DoesNotExist:
            # Run default password hasher to prevent timing attacks
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None