from django.db import models
from accounts.models import LandType, AccessType

class BuyerProfile(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name

class BuyBoxFilter(models.Model):
    buyer = models.OneToOneField(BuyerProfile, on_delete=models.CASCADE, related_name='buy_box')

    # Asset Type
    ASSET_TYPE_CHOICES = [
        ('land', 'Land'),
        ('houses', 'Houses'),
        ('both', 'Both'),
    ]
    asset_type = models.CharField(max_length=10, choices=ASSET_TYPE_CHOICES)

    # Active Buyer
    is_active_buyer = models.BooleanField(default=True)

    # Blacklist Status
    is_blacklisted = models.BooleanField(default=False)

    # Location Preferences
    preferred_cities = models.JSONField(default=list, blank=True)
    preferred_counties = models.JSONField(default=list, blank=True)
    preferred_states = models.JSONField(default=list, blank=True)
    preferred_zip_codes = models.JSONField(default=list, blank=True)

    # Investment Strategies – Add others similarly...
    house_strategies = models.JSONField(default=list, blank=True)
    land_strategies = models.JSONField(default=list, blank=True)

    # Desired Property Types
    house_property_types = models.JSONField(default=list, blank=True)
    land_property_types = models.JSONField(default=list, blank=True)

    # Ranges and Preferences
    price_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    lot_size_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    lot_size_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bedroom_min = models.IntegerField(null=True, blank=True)
    bathroom_min = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    sqft_min = models.IntegerField(null=True, blank=True)
    sqft_max = models.IntegerField(null=True, blank=True)
    year_built_min = models.IntegerField(null=True, blank=True)
    year_built_max = models.IntegerField(null=True, blank=True)
    
    land_type = models.ForeignKey(LandType, on_delete=models.SET_NULL, null=True, blank=True)
    access_type = models.ForeignKey(AccessType, on_delete=models.SET_NULL, null=True, blank=True)
    zoning = models.JSONField(default=list, blank=True)

    # Rehab Restrictions
    restricted_rehabs = models.JSONField(default=list, blank=True)
    specialty_rehab_avoidance = models.JSONField(default=list, blank=True)

    # Strict Requirements
    strict_requirements = models.JSONField(default=list, blank=True)

    # Location Characteristics
    location_characteristics = models.JSONField(default=list, blank=True)

    # Property Characteristics
    property_characteristics = models.JSONField(default=list, blank=True)

    # Internal notes
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"BuyBox for {self.buyer.name}"