from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserSignupView,
    UserLoginView,
    GoogleAuthView,
    AdminSignupView,
    AdminLoginView,
    LogoutView,
    MeView,
    AdminRegenerateCodeView,
)

app_name = 'users'

urlpatterns = [
    # ── Regular auth ──────────────────────────────────
    path('auth/signup/',        UserSignupView.as_view(),  name='user-signup'),
    path('auth/login/',         UserLoginView.as_view(),   name='user-login'),
    path('auth/logout/',        LogoutView.as_view(),      name='logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(),name='token-refresh'),

    # ── Google OAuth ──────────────────────────────────
    path('auth/google/',        GoogleAuthView.as_view(),  name='google-auth'),

    # ── Admin auth ────────────────────────────────────
    path('auth/admin/signup/',       AdminSignupView.as_view(),        name='admin-signup'),
    path('auth/admin/login/',        AdminLoginView.as_view(),         name='admin-login'),
    path('auth/admin/regen-code/',   AdminRegenerateCodeView.as_view(),name='admin-regen-code'),

    # ── Profile ──────────────────────────────────────
    path('users/me/', MeView.as_view(), name='me'),
]