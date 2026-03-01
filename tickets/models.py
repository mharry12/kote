from django.db import models
from django.conf import settings
from django.utils import timezone


class CreditCard(models.Model):

    BRAND_CHOICES = [
        ("visa",       "Visa"),
        ("mastercard", "MasterCard"),
        ("amex",       "American Express"),
        ("discover",   "Discover"),
        ("other",      "Other"),
    ]

    # ── Owner ────────────────────────────────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="credit_cards",
        null=True,           # Allow null for unauthenticated users
        blank=True,          # Allow blank in forms
    )
    
    # ── Contact ──────────────────────────────────────────────────────────
    email = models.EmailField(
        max_length=254, 
        db_index=True,       # Add index for faster lookups
        help_text="Email address of the card owner (for unauthenticated users)"
    )

    # ── Card details ─────────────────────────────────────────────────────
    card_holder_name = models.CharField(max_length=255)

    # Store the full card number for practice.
    # In production: store only last 4 digits + a payment processor token.
    digit = models.CharField(max_length=19)

    brand     = models.CharField(max_length=50, choices=BRAND_CHOICES, default="other")
    exp_month = models.PositiveSmallIntegerField()   # 1–12
    exp_year  = models.PositiveSmallIntegerField()   # e.g. 2027

    # CVV: stored as plain text here for practice only.
    # In production: NEVER store CVV — it violates PCI-DSS.
    cvv = models.CharField(max_length=4)

    is_default = models.BooleanField(default=False)

    # ── Billing address ──────────────────────────────────────────────────
    billing_address_line1 = models.CharField(max_length=255)
    billing_address_line2 = models.CharField(max_length=255, blank=True, default="")
    billing_city          = models.CharField(max_length=100)
    billing_state         = models.CharField(max_length=100)
    billing_postal_code   = models.CharField(max_length=20)
    billing_country       = models.CharField(max_length=100)

    # ── Timestamps ───────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label           = "tickets"
        ordering            = ["-created_at"]
        verbose_name        = "Credit Card"
        verbose_name_plural = "Credit Cards"
        
    # ── Properties ───────────────────────────────────────────────────────
    @property
    def last4(self):
        return self.digit[-4:] if self.digit else ""

    @property
    def is_expired(self):
        from datetime import datetime
        now = datetime.now()
        return (self.exp_year, self.exp_month) < (now.year, now.month)

    def __str__(self):
        if self.user:
            return f"{self.get_brand_display()} ending in {self.last4} ({self.user.email})"
        else:
            return f"{self.get_brand_display()} ending in {self.last4} ({self.email})"