from django.urls import path
from .views import (
    CreditCardCreateView,
    CreditCardDetailView,
    SetDefaultCardView,
    AdminCreditCardListView,
)

app_name = 'tickets'

urlpatterns = [
    # User endpoints
    path("cards/",                       CreditCardCreateView.as_view(),  name="card-create"),  # Removed trailing slash
    path("cards/<int:pk>",              CreditCardDetailView.as_view(),  name="card-detail"),  # Removed trailing slash
    path("cards/<int:pk>/set-default",  SetDefaultCardView.as_view(),    name="card-set-default"),  # Removed trailing slash

    # Admin endpoint
    path("admin/credit-cards",          AdminCreditCardListView.as_view(), name="admin-credit-card-list"),  # Removed trailing slash
]