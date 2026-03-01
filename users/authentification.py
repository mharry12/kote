"""
Authentication utilities — token generation, blacklisting, custom JWT claims.
"""
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model

User = get_user_model()


# ── Token generation ────────────────────────────────────────────────────
def get_tokens_for_user(user):
    """Return a fresh access + refresh token pair for the given user."""
    refresh = RefreshToken.for_user(user)

    # Add custom claims
    refresh['email'] = user.email
    refresh['role']  = user.role
    refresh['name']  = user.full_name

    return {
        'refresh': str(refresh),
        'access':  str(refresh.access_token),
    }


def blacklist_refresh_token(refresh_token_str: str):
    """
    Blacklist a refresh token (used on logout).
    Requires 'rest_framework_simplejwt.token_blacklist' in INSTALLED_APPS.
    """
    try:
        token = RefreshToken(refresh_token_str)
        token.blacklist()
    except TokenError:
        pass  # already blacklisted or invalid — ignore


# ── Custom JWT authentication (optional override) ───────────────────────
class CustomJWTAuthentication(JWTAuthentication):
    """
    Extends the default JWT auth to attach the full user object
    and validate the token's role claim.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result

        # Optionally enforce role matches DB (defense against stale tokens)
        token_role = token.payload.get('role')
        if token_role and token_role != user.role:
            raise AuthenticationFailed('Token role mismatch. Please log in again.')

        return user, token