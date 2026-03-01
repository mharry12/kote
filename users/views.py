from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.contrib.auth import get_user_model

from .serializers import (
    UserSerializer,
    UserSignupSerializer,
    LoginSerializer,
    GoogleAuthSerializer,
    AdminSignupSerializer,
    AdminLoginSerializer,
)
from .authentification import get_tokens_for_user, blacklist_refresh_token
from .google import verify_google_id_token
from .permissions import IsAdminUser

User = get_user_model()


# ── Global exception handler ─────────────────────────────────────────────
def custom_exception_handler(exc, context):
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            'success': False,
            'message': _flatten_errors(response.data),
            'data':    None,
        }
    return response


def _flatten_errors(data):
    if isinstance(data, list):
        return ' '.join(str(e) for e in data)
    if isinstance(data, dict):
        msgs = []
        for v in data.values():
            msgs.append(_flatten_errors(v))
        return ' '.join(msgs)
    return str(data)


def success_response(data=None, message='Success', status_code=status.HTTP_200_OK):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)


def error_response(message='Error', status_code=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'message': message, 'data': None}, status=status_code)


# ════════════════════════════════════════════════════
#  USER SIGN-UP
# ════════════════════════════════════════════════════
class UserSignupView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary='Register a new user',
        request_body=UserSignupSerializer,
        responses={
            201: openapi.Response('Created', schema=openapi.Schema(type=openapi.TYPE_OBJECT)),
            400: 'Validation error',
        },
        tags=['Auth — User'],
    )
    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(_flatten_errors(serializer.errors))

        user   = serializer.save()
        tokens = get_tokens_for_user(user)
        return success_response(
            data={'user': UserSerializer(user).data, 'tokens': tokens},
            message='Account created successfully.',
            status_code=status.HTTP_201_CREATED,
        )


# ════════════════════════════════════════════════════
#  USER LOGIN
# ════════════════════════════════════════════════════
class UserLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary='Login with email and password',
        request_body=LoginSerializer,
        responses={200: 'OK', 400: 'Invalid credentials'},
        tags=['Auth — User'],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return error_response(_flatten_errors(serializer.errors))

        user   = serializer.validated_data['user']
        tokens = get_tokens_for_user(user)
        return success_response(
            data={'user': UserSerializer(user).data, 'tokens': tokens},
            message='Login successful.',
        )


# ════════════════════════════════════════════════════
#  GOOGLE SIGN-UP / LOGIN
# ════════════════════════════════════════════════════
class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary='Sign in / register with a Google ID token',
        request_body=GoogleAuthSerializer,
        responses={200: 'OK', 400: 'Invalid token'},
        tags=['Auth — Social'],
    )
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(_flatten_errors(serializer.errors))

        id_token = serializer.validated_data['id_token']

        try:
            profile = verify_google_id_token(id_token)
        except ValueError as exc:
            return error_response(str(exc), status_code=status.HTTP_401_UNAUTHORIZED)

        google_id  = profile['google_id']
        email      = profile['email']
        first_name = profile['first_name']
        last_name  = profile['last_name']

        # Try to find an existing user by google_id first, then by email
        user = (
            User.objects.filter(google_id=google_id).first()
            or User.objects.filter(email=email).first()
        )

        created = False
        if user:
            # Link google_id if logging in via email account for first time
            if not user.google_id:
                user.google_id = google_id
                user.auth_provider = 'google'
                user.save(update_fields=['google_id', 'auth_provider'])
        else:
            user = User.objects.create_user(
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=None,           # no password for OAuth users
                google_id=google_id,
                auth_provider='google',
                is_verified=True,
            )
            created = True

        tokens = get_tokens_for_user(user)
        return success_response(
            data={'user': UserSerializer(user).data, 'tokens': tokens, 'created': created},
            message='Google authentication successful.',
        )


# ════════════════════════════════════════════════════
#  ADMIN SIGN-UP
# ════════════════════════════════════════════════════
class AdminSignupView(APIView):
    """
    Creates an admin account.
    The plain access_code is returned ONCE — it cannot be retrieved again.
    In production this endpoint should be restricted to superusers only.
    """
    permission_classes = [AllowAny]   # ← tighten in production: IsAdminUser

    @swagger_auto_schema(
        operation_summary='Register a new admin account',
        request_body=AdminSignupSerializer,
        responses={201: 'Created — includes one-time access code', 400: 'Validation error'},
        tags=['Auth — Admin'],
    )
    def post(self, request):
        serializer = AdminSignupSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(_flatten_errors(serializer.errors))

        user   = serializer.save()
        tokens = get_tokens_for_user(user)

        return success_response(
            data={
                'user':        UserSerializer(user).data,
                'tokens':      tokens,
                'access_code': user._plain_access_code,   # shown once
                'warning':     'Store this access code securely. It will not be shown again.',
            },
            message='Admin account created.',
            status_code=status.HTTP_201_CREATED,
        )


# ════════════════════════════════════════════════════
#  ADMIN LOGIN
# ════════════════════════════════════════════════════
class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary='Admin login — requires email, password, and 8-char access code',
        request_body=AdminLoginSerializer,
        responses={200: 'OK', 400: 'Invalid credentials or access code'},
        tags=['Auth — Admin'],
    )
    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return error_response(_flatten_errors(serializer.errors))

        user   = serializer.validated_data['user']
        tokens = get_tokens_for_user(user)
        return success_response(
            data={'user': UserSerializer(user).data, 'tokens': tokens},
            message='Admin login successful.',
        )


# ════════════════════════════════════════════════════
#  LOGOUT
# ════════════════════════════════════════════════════
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='Logout — blacklist the refresh token',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['refresh'],
            properties={'refresh': openapi.Schema(type=openapi.TYPE_STRING)},
        ),
        responses={200: 'Logged out', 400: 'Bad request'},
        tags=['Auth — User'],
    )
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return error_response('refresh token is required.')
        blacklist_refresh_token(refresh_token)
        return success_response(message='Logged out successfully.')


# ════════════════════════════════════════════════════
#  PROFILE (me)
# ════════════════════════════════════════════════════
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='Get current user profile',
        responses={200: UserSerializer},
        tags=['User'],
    )
    def get(self, request):
        return success_response(data=UserSerializer(request.user).data)

    @swagger_auto_schema(
        operation_summary='Update current user profile',
        request_body=UserSerializer,
        responses={200: UserSerializer},
        tags=['User'],
    )
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(_flatten_errors(serializer.errors))
        serializer.save()
        return success_response(data=serializer.data, message='Profile updated.')


# ════════════════════════════════════════════════════
#  ADMIN — regenerate access code
# ════════════════════════════════════════════════════
class AdminRegenerateCodeView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @swagger_auto_schema(
        operation_summary='Regenerate your admin access code (old code is invalidated)',
        responses={200: 'New code returned once'},
        tags=['Auth — Admin'],
    )
    def post(self, request):
        new_code = request.user.generate_and_save_access_code()
        return success_response(
            data={'access_code': new_code, 'warning': 'Store this securely. It will not be shown again.'},
            message='Access code regenerated.',
        )