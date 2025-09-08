from django.urls import path
from .views import (
    BuyerProfileCreateView, 
    BuyBoxFilterUpsertView, 
    MatchPropertyToBuyersView, 
    BuyerProfileListView, 
    BuyerProfileDetailView, 
    BuyerMatchingStatsView,
    PublicBuyBoxCriteriaListView,
    BuyerProfileDeleteView,
    BuyBoxToggleActiveView,
    BuyerDealLogCreateView,
    BuyerDealLogListView,
    BuyerDealDetailView,
    BuyerDealResponseView,
)

urlpatterns = [
    path('buyers/create/', BuyerProfileCreateView.as_view(), name='buyer-create'),
    path('buyers/<int:buyer_id>/delete/', BuyerProfileDeleteView.as_view(), name='buyer-delete'),
    path('buyers/', BuyerProfileListView.as_view(), name='buyer-list'),
    path('buyers/<int:buyer_id>/', BuyerProfileDetailView.as_view(), name='buyer-detail'),
    path("buyers/<int:buyer_id>/buy-box/", BuyBoxFilterUpsertView.as_view(), name="buybox-upsert"),
    path('properties/<int:pk>/match-buyers/', MatchPropertyToBuyersView.as_view(), name='match-property-buyers'),
    path('buyers/<int:buyer_id>/matching-stats/', BuyerMatchingStatsView.as_view(), name='buyer-matching-stats'),
    
    path('public/buybox-criteria/', PublicBuyBoxCriteriaListView.as_view(), name='public-buybox-criteria'),
    path('buyers/<int:buyer_id>/buybox/toggle/', BuyBoxToggleActiveView.as_view(), name='buybox-toggle'),
    
    path("buyers/send-to-buyer/", BuyerDealLogCreateView.as_view(), name="send-deal-to-buyer"),

    # Get all deal logs for a particular buyer
    path("buyers/<int:buyer_id>/deal-logs/", BuyerDealLogListView.as_view(), name="buyer-deal-logs"),
    path("buyer-deals/<int:pk>/", BuyerDealDetailView.as_view(), name="buyer-deal-detail"),
    path("buyer-deals/<int:pk>/response/", BuyerDealResponseView.as_view(), name="buyer-deal-response"),

]