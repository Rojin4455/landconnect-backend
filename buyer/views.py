from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import BuyerProfile, BuyBoxFilter
from .serializers import BuyerProfileSerializer, BuyBoxFilterSerializer
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from data_management_app.models import PropertySubmission
from .utils import match_property_to_buyers
from rest_framework.response import Response


class BuyerProfileCreateView(generics.CreateAPIView):
    queryset = BuyerProfile.objects.all()
    serializer_class = BuyerProfileSerializer
    permission_classes = [IsAuthenticated]

class BuyBoxFilterUpsertView(generics.CreateAPIView):
    serializer_class = BuyBoxFilterSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        buyer_id = self.kwargs.get('buyer_id')
        try:
            buyer = BuyerProfile.objects.get(id=buyer_id)
        except BuyerProfile.DoesNotExist:
            raise NotFound("BuyerProfile not found.")
        
        # If a BuyBoxFilter already exists for this buyer, update it
        instance, created = BuyBoxFilter.objects.update_or_create(
            buyer=buyer,
            defaults=serializer.validated_data
        )
        serializer.instance = instance

class BuyBoxFilterRetrieveView(generics.RetrieveAPIView):
    serializer_class = BuyBoxFilterSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        buyer_id = self.kwargs.get("buyer_id")
        try:
            return BuyBoxFilter.objects.get(buyer__id=buyer_id)
        except BuyBoxFilter.DoesNotExist:
            raise NotFound("BuyBoxFilter not found for this buyer.")
        

class MatchPropertyToBuyersView(APIView):
    def get(self, request, pk):
        try:
            property_instance = PropertySubmission.objects.select_related("land_type").prefetch_related("access_type", "utilities").get(pk=pk)
        except PropertySubmission.DoesNotExist:
            return Response({"detail": "Property not found."}, status=404)
        
        matches = match_property_to_buyers(property_instance)
        return Response({"matches": matches}, status=200)