import secrets
import string
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from .managers import UserManager


def generate_access_code(length=8):
    """Generate a cryptographically secure alphanumeric access code."""
    alphabet = string.ascii_letters + string.digits   # A-Za-z0-9
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model.
    - Regular users authenticate with email + password (or Google OAuth).
    - Admin users additionally require an 8-char alphanumeric access code.
    """

    class Role(models.TextChoices):
        USER  = 'user',  'User'
        ADMIN = 'admin', 'Admin'

    # ── Core fields ─────────────────────────────────
    email      = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name  = models.CharField(max_length=100, blank=True)
    avatar     = models.ImageField(upload_to='avatars/', null=True, blank=True)

    # ── Role & status ───────────────────────────────
    role       = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)   # Django admin site access
    is_verified= models.BooleanField(default=False)   # email verification flag

    # ── Google OAuth ─────────────────────────────────
    google_id  = models.CharField(max_length=200, unique=True, null=True, blank=True)
    auth_provider = models.CharField(
        max_length=20,
        choices=[('email', 'Email'), ('google', 'Google')],
        default='email',
    )

    # ── Admin access code ────────────────────────────
    # Stored hashed in production; here we keep it plain for simplicity.
    # Replace with a proper hashed field or django-encrypted-model-fields in prod.
    access_code = models.CharField(max_length=8, blank=True, default='')

    # ── Timestamps ──────────────────────────────────
    date_joined = models.DateTimeField(default=timezone.now)
    last_login  = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name      = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email

    def is_admin_user(self):
        return self.role == self.Role.ADMIN

    def generate_and_save_access_code(self):
        """Generate a fresh access code, save and return it (shown once)."""
        code = generate_access_code()
        self.access_code = code
        self.save(update_fields=['access_code'])
        return code

    def verify_access_code(self, code: str) -> bool:
        return self.access_code == code