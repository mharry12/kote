import datetime
from rest_framework import serializers
from .models import CreditCard


class CreditCardSerializer(serializers.ModelSerializer):
    last4 = serializers.CharField(read_only=True)
    
    # For PRACTICE only - CVV will be returned in GET responses
    # In production, NEVER do this!
    cvv = serializers.CharField(max_length=4, required=True)

    class Meta:
        model = CreditCard
        fields = [
            "id",
            "email",
            "card_holder_name",
            "digit",
            "last4",
            "brand",
            "cvv",  # Now this will be returned in GET responses
            "exp_month",
            "exp_year",
            "is_default",
            "billing_address_line1",
            "billing_address_line2",
            "billing_city",
            "billing_state",
            "billing_postal_code",
            "billing_country",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last4", "created_at", "updated_at"]

    def validate_email(self, value):
        """Basic email validation"""
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value.lower()

    def validate_digit(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Card number must contain digits only.")
        if not (13 <= len(value) <= 19):
            raise serializers.ValidationError("Card number must be 13–19 digits.")
        return value

    def validate_exp_month(self, value):
        if not (1 <= value <= 12):
            raise serializers.ValidationError("Expiry month must be between 1 and 12.")
        return value

    def validate_exp_year(self, value):
        if value < datetime.datetime.now().year:
            raise serializers.ValidationError("Expiry year cannot be in the past.")
        return value

    def validate_cvv(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("CVV must contain digits only.")
        if not (3 <= len(value) <= 4):
            raise serializers.ValidationError("CVV must be 3 or 4 digits.")
        return value

    def validate(self, data):
        now = datetime.datetime.now()
        exp_month = data.get("exp_month")
        exp_year = data.get("exp_year")

        if exp_year and exp_month:
            if exp_year == now.year and exp_month < now.month:
                raise serializers.ValidationError({"exp_month": "This card has expired."})

        required_billing = [
            "billing_address_line1",
            "billing_city",
            "billing_state",
            "billing_postal_code",
            "billing_country",
        ]
        errors = {}
        for field in required_billing:
            if field in data and not str(data[field]).strip():
                label = field.replace("billing_", "").replace("_", " ").title()
                errors[field] = f"{label} is required."
        if errors:
            raise serializers.ValidationError(errors)

        return data

    def create(self, validated_data):
        """Ensure email is stored and user is set if authenticated"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class CreditCardAdminSerializer(CreditCardSerializer):
    """
    Admin view: includes card owner's email and user id.
    """
    user_email = serializers.EmailField(source="user.email", read_only=True, allow_null=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True, allow_null=True)

    class Meta(CreditCardSerializer.Meta):
        fields = ["user_id", "user_email"] + CreditCardSerializer.Meta.fields