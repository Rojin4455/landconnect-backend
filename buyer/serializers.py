from rest_framework import serializers
from .models import BuyerProfile, BuyBoxFilter, BuyerDealLog
from data_management_app.serializers import PropertySubmissionSerializer
# from ghl_accounts.utils import create_ghl_contact
# from ghl_accounts.models import GHLAuthCredentials

class BuyerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerProfile
        fields = '__all__'

        
class BuyBoxFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyBoxFilter
        fields = '__all__'
        read_only_fields = ['buyer']
        
        
class BuyerDealLogSerializer(serializers.ModelSerializer):
    buyer_name = serializers.CharField(source="buyer.name", read_only=True)
    deal_address = serializers.CharField(source="deal.address", read_only=True)

    class Meta:
        model = BuyerDealLog
        fields = ["id", "buyer", "buyer_name", "deal", "deal_address", "status", "sent_date", "match_score"]
        read_only_fields = ["sent_date"]
        
class BuyerDealDetailSerializer(serializers.ModelSerializer):
    deal = PropertySubmissionSerializer(read_only=True)
    buyer_name = serializers.CharField(source="buyer.name", read_only=True)

    class Meta:
        model = BuyerDealLog
        fields = [
            "id", "buyer", "buyer_name",
            "deal", "status", "sent_date", "match_score"
        ]
        read_only_fields = ["buyer", "buyer_name", "deal", "sent_date", "match_score"]
