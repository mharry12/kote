from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# ── Swagger / ReDoc ──────────────────────────────────────────────────────
schema_view = get_schema_view(
    openapi.Info(
        title='KNGEGO API',
        default_version='v1',
        description='Authentication & user management API',
        contact=openapi.Contact(email='admin@kngego.com'),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # Django admin
    path('django-admin/', admin.site.urls),

    # API v1
    path('api/v1/', include('users.urls')),
    path('api/v1/', include('tickets.urls')),

    # Swagger UI
    path('api/docs/',   schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/',  schema_view.with_ui('redoc',   cache_timeout=0), name='schema-redoc'),
    path('api/schema/', schema_view.without_ui(cache_timeout=0),         name='schema-json'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)