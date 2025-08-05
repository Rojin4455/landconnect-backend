from rest_framework import serializers
from .models import BuyerProfile, BuyBoxFilter

class BuyerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerProfile
        fields = '__all__'
        
class BuyBoxFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyBoxFilter
        fields = '__all__'
        read_only_fields = ['buyer']