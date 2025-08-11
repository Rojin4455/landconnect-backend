from django.urls import path
from .views import (
    BuyerProfileCreateView, 
    BuyBoxFilterUpsertView, 
    MatchPropertyToBuyersView, 
    BuyerProfileListView, 
    BuyerProfileDetailView, 
    BuyerMatchingStatsView,
    PublicBuyBoxCriteriaListView
)

urlpatterns = [
    path('buyers/create/', BuyerProfileCreateView.as_view(), name='buyer-create'),
    path('buyers/', BuyerProfileListView.as_view(), name='buyer-list'),
    path('buyers/<int:buyer_id>/', BuyerProfileDetailView.as_view(), name='buyer-detail'),
    path("buyers/<int:buyer_id>/buy-box/", BuyBoxFilterUpsertView.as_view(), name="buybox-upsert"),
    path('properties/<int:pk>/match-buyers/', MatchPropertyToBuyersView.as_view(), name='match-property-buyers'),
    path('buyers/<int:buyer_id>/matching-stats/', BuyerMatchingStatsView.as_view(), name='buyer-matching-stats'),
    
    path('public/buybox-criteria/', PublicBuyBoxCriteriaListView.as_view(), name='public-buybox-criteria'),
]