from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User


# ── Helpers ─────────────────────────────────────────────────────────────
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access':  str(refresh.access_token),
    }


# ── User representation ──────────────────────────────────────────────────
class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'auth_provider', 'is_verified', 'avatar', 'date_joined',
        ]
        read_only_fields = ['id', 'role', 'auth_provider', 'is_verified', 'date_joined']


# ── Regular Sign-up ─────────────────────────────────────────────────────
class UserSignupSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label='Confirm password')

    class Meta:
        model  = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


# ── Regular Login ────────────────────────────────────────────────────────
class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email    = attrs['email'].lower().strip()
        password = attrs['password']
        user = authenticate(request=self.context.get('request'), email=email, password=password)
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('This account has been deactivated.')
        attrs['user'] = user
        return attrs


# ── Google OAuth ─────────────────────────────────────────────────────────
class GoogleAuthSerializer(serializers.Serializer):
    """
    Accepts a Google ID token from the frontend.
    The view will verify it and create/fetch the user.
    """
    id_token = serializers.CharField()


# ── Admin Sign-up ────────────────────────────────────────────────────────
class AdminSignupSerializer(serializers.ModelSerializer):
    """
    Creates an admin account.
    The generated access_code is returned once in the response.
    """
    password  = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label='Confirm password')

    class Meta:
        model  = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        user, code = User.objects.create_admin(**validated_data)
        # Stash the plain code temporarily so the view can return it
        user._plain_access_code = code
        return user


# ── Admin Login ───────────────────────────────────────────────────────────
class AdminLoginSerializer(serializers.Serializer):
    """
    Admin logs in with email + password + 8-char access code.
    """
    email       = serializers.EmailField()
    password    = serializers.CharField(write_only=True)
    access_code = serializers.CharField(min_length=8, max_length=8)

    def validate(self, attrs):
        email       = attrs['email'].lower().strip()
        password    = attrs['password']
        access_code = attrs['access_code']

        user = authenticate(request=self.context.get('request'), email=email, password=password)
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('This account has been deactivated.')
        if not user.is_admin_user():
            raise serializers.ValidationError('Access denied: not an admin account.')
        if not user.verify_access_code(access_code):
            raise serializers.ValidationError('Invalid access code.')

        attrs['user'] = user
        return attrs


# ── Token refresh (re-exported for clarity) ──────────────────────────────
class TokenResponseSerializer(serializers.Serializer):
    """Used only for Swagger schema documentation."""
    access  = serializers.CharField()
    refresh = serializers.CharField()
    user    = UserSerializer()