"""
Google ID token verification.

Flow:
  1. Frontend signs the user in with Google (e.g. Google One-Tap or OAuth popup).
  2. Frontend sends the raw id_token to our API.
  3. This module verifies the token against Google's public keys.
  4. Returns a dict with the user's profile information.

Dependencies: PyJWT (already installed) + requests.
"""
import requests
from django.conf import settings


GOOGLE_CERTS_URL = 'https://www.googleapis.com/oauth2/v3/certs'
GOOGLE_ISSUER    = ('https://accounts.google.com', 'accounts.google.com')


def _get_google_public_keys():
    """Fetch Google's current public JWK set."""
    response = requests.get(GOOGLE_CERTS_URL, timeout=5)
    response.raise_for_status()
    return response.json()


def verify_google_id_token(id_token: str) -> dict:
    """
    Verify a Google ID token and return the decoded payload.

    Returns:
        {
            'sub':            str,   # Google user ID
            'email':          str,
            'email_verified': bool,
            'name':           str,
            'given_name':     str,
            'family_name':    str,
            'picture':        str,
        }

    Raises:
        ValueError: if the token is invalid, expired, or issued for a
                    different client.
    """
    import jwt
    from jwt import PyJWKClient

    try:
        jwks_client = PyJWKClient(GOOGLE_CERTS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)

        payload = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=['RS256'],
            audience=settings.GOOGLE_CLIENT_ID,
            issuer=GOOGLE_ISSUER,
        )
    except jwt.ExpiredSignatureError:
        raise ValueError('Google token has expired.')
    except jwt.InvalidAudienceError:
        raise ValueError('Google token audience mismatch.')
    except jwt.PyJWTError as exc:
        raise ValueError(f'Google token invalid: {exc}')

    if not payload.get('email_verified'):
        raise ValueError('Google email is not verified.')

    return {
        'google_id':    payload['sub'],
        'email':        payload['email'],
        'email_verified': payload.get('email_verified', False),
        'first_name':   payload.get('given_name', ''),
        'last_name':    payload.get('family_name', ''),
        'full_name':    payload.get('name', ''),
        'avatar':       payload.get('picture', ''),
    }