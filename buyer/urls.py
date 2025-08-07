from django.urls import path
from .views import BuyerProfileCreateView, BuyBoxFilterUpsertView, BuyBoxFilterRetrieveView, MatchPropertyToBuyersView, BuyerProfileDetailView

urlpatterns = [
    path('buyers/create/', BuyerProfileCreateView.as_view(), name='buyer-create'),
    path('buyers/', BuyerProfileDetailView.as_view(), name='buyer-list'),
    path("buyers/<int:buyer_id>/buy-box/", BuyBoxFilterUpsertView.as_view(), name="buybox-upsert"),
    path("buyers/<int:buyer_id>/buy-box/view/", BuyBoxFilterRetrieveView.as_view(), name="buybox-view"),
    path('properties/<int:pk>/match-buyers/', MatchPropertyToBuyersView.as_view(), name='match-property-buyers'),

]
