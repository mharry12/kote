from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CreditCard
from .serializers import CreditCardSerializer, CreditCardAdminSerializer
from .permissions import IsAdminWithAccessCode


# ════════════════════════════════════════════════════
#  USER — Add a card (no authentication required)
# ════════════════════════════════════════════════════
class CreditCardCreateView(generics.CreateAPIView):
    """
    POST /api/v1/tickets/cards/
    Any user (authenticated or not) can save a card.
    First card added for an email is automatically set as default.
    """
    serializer_class = CreditCardSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        email = serializer.validated_data.get('email')
        is_first = not CreditCard.objects.filter(email=email).exists()
        
        # The serializer's create method will handle setting the user
        serializer.save(is_default=is_first)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"success": True, "message": "Card added successfully.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )


# ════════════════════════════════════════════════════
#  USER — View / Update / Delete own card (requires email)
# ════════════════════════════════════════════════════
class CreditCardDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/tickets/cards/<pk>/?email=user@example.com
    PATCH  /api/v1/tickets/cards/<pk>/?email=user@example.com
    DELETE /api/v1/tickets/cards/<pk>/?email=user@example.com
    """
    serializer_class = CreditCardSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        email = self.request.query_params.get('email')
        if not email:
            return CreditCard.objects.none()
        return CreditCard.objects.filter(email=email)

    def get_object(self):
        queryset = self.get_queryset()
        obj = generics.get_object_or_404(queryset, pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        new_default = serializer.validated_data.get("is_default", instance.is_default)

        with transaction.atomic():
            if new_default and not instance.is_default:
                CreditCard.objects.filter(
                    email=instance.email, is_default=True
                ).exclude(pk=instance.pk).update(is_default=False)
            self.perform_update(serializer)

        # If user is authenticated, link the card to their account
        if request.user.is_authenticated and not instance.user:
            instance.user = request.user
            instance.save(update_fields=['user'])

        return Response(
            {"success": True, "message": "Card updated.", "data": serializer.data}
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        was_default = instance.is_default
        email = instance.email

        with transaction.atomic():
            self.perform_destroy(instance)
            if was_default:
                next_card = CreditCard.objects.filter(
                    email=email
                ).order_by("-created_at").first()
                if next_card:
                    next_card.is_default = True
                    next_card.save(update_fields=["is_default"])

        return Response(
            {"success": True, "message": "Card deleted."},
            status=status.HTTP_200_OK,
        )


# ════════════════════════════════════════════════════
#  USER — Set a card as default
# ════════════════════════════════════════════════════
class SetDefaultCardView(APIView):
    """
    POST /api/v1/tickets/cards/<pk>/set-default/?email=user@example.com
    """
    permission_classes = [AllowAny]

    def post(self, request, pk):
        email = request.query_params.get('email')
        if not email:
            return Response(
                {"success": False, "message": "Email parameter required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            card = CreditCard.objects.get(pk=pk, email=email)
        except CreditCard.DoesNotExist:
            return Response(
                {"success": False, "message": "Card not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            CreditCard.objects.filter(
                email=email, is_default=True
            ).exclude(pk=card.pk).update(is_default=False)
            card.is_default = True
            card.save(update_fields=["is_default"])

        return Response({"success": True, "message": "Default card updated."})


# ════════════════════════════════════════════════════
#  ADMIN — GET all cards
# ════════════════════════════════════════════════════
class AdminCreditCardListView(generics.ListAPIView):
    """
    GET /api/v1/tickets/admin/credit-cards/
    Requires admin authentication + access code.
    """
    serializer_class = CreditCardAdminSerializer
    permission_classes = [IsAdminWithAccessCode]

    def get_queryset(self):
        qs = CreditCard.objects.select_related("user").all()
        email = self.request.query_params.get("email")
        if email:
            qs = qs.filter(email__iexact=email)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response({
            "success": True,
            "count": qs.count(),
            "data": serializer.data,
        })