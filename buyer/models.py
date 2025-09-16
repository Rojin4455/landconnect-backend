from django.db import models
from accounts.models import LandType, AccessType, Utility
from data_management_app.models import PropertySubmission

class BuyerProfile(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    ghl_contact_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class BuyBoxFilter(models.Model):
    buyer = models.OneToOneField(BuyerProfile, on_delete=models.CASCADE, related_name='buy_box')

    # Asset Type - What they buy
    ASSET_TYPE_CHOICES = [
        ('land', 'Land'),
        ('houses', 'Houses'),
        ('both', 'Both'),
    ]
    asset_type = models.CharField(max_length=10, choices=ASSET_TYPE_CHOICES)

    # Active Buyer Status
    is_active_buyer = models.BooleanField(default=True)

    # Blacklist Status
    is_blacklisted = models.BooleanField(default=False)

    # Location Preferences
    address = models.CharField(max_length=500)

    # Investment Strategies
    HOUSE_STRATEGY_CHOICES = [
        ('fix_flip', 'Fix & Flip'),
        ('buy_hold', 'Buy & Hold (Rental)'),
        ('brrrr', 'BRRRR'),
        ('airbnb', 'Airbnb / Short-Term Rental'),
        ('novation', 'Novation / Creative Finance'),
    ]
    
    LAND_STRATEGY_CHOICES = [
        ('infill_development', 'Infill Lot Development'),
        ('buy_flip', 'Buy & Flip'),
        ('buy_hold', 'Buy & Hold'),
        ('subdivide_sell', 'Subdivide & Sell'),
        ('seller_financing', 'Seller Financing'),
        ('rv_lot', 'RV Lot / Tiny Home Lot / Mobile Home Lot'),
        ('entitlement', 'Entitlement / Rezoning'),
    ]
    
    house_strategies = models.JSONField(default=list, blank=True)
    land_strategies = models.JSONField(default=list, blank=True)

    # Desired Property Types
    HOUSE_PROPERTY_TYPES = [
        ('single_family', 'Single Family'),
        ('duplex_triplex', 'Duplex / Triplex'),
        ('mobile_home', 'Mobile Home with Land'),
        ('townhouse', 'Townhouse'),
        ('condo', 'Condo'),
    ]
    
    LAND_PROPERTY_TYPES = [
        ('residential_vacant', 'Residential Vacant'),
        ('agricultural', 'Agricultural'),
        ('commercial', 'Commercial'),
        ('recreational', 'Recreational'),
        ('timberland', 'Timberland / Hunting'),
        ('waterfront', 'Waterfront'),
        ('subdividable', 'Subdividable'),
    ]
    
    house_property_types = models.JSONField(default=list, blank=True)
    land_property_types = models.JSONField(default=list, blank=True)

    # Price Range
    price_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Lot Size (for land)
    lot_size_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    lot_size_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # House-specific preferences
    bedroom_min = models.IntegerField(null=True, blank=True)
    bathroom_min = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    sqft_min = models.IntegerField(null=True, blank=True)
    sqft_max = models.IntegerField(null=True, blank=True)
    year_built_min = models.IntegerField(null=True, blank=True)
    year_built_max = models.IntegerField(null=True, blank=True)

    # Land-specific preferences
    # land_type = models.ForeignKey(LandType, on_delete=models.SET_NULL, null=True, blank=True)
    access_type = models.ForeignKey(AccessType, on_delete=models.SET_NULL, null=True, blank=True)
    preferred_utility = models.ForeignKey(Utility, on_delete=models.SET_NULL, null=True, blank=True)
    zoning = models.JSONField(default=list, blank=True, help_text="List of acceptable zoning types")

    # Rehab Restrictions
    RESTRICTED_REHAB_CHOICES = [
        ('major_foundation', 'Major Foundation'),
        ('fire_damage', 'Fire Damage'),
        ('mold', 'Mold'),
        ('full_gut', 'Full Gut'),
        ('termite', 'Termite'),
        ('roof_replacement', 'Roof Replacement'),
    ]
    
    SPECIALTY_REHAB_CHOICES = [
        ('septic', 'Septic'),
        ('electrical_panel', 'Electrical Panel'),
        ('full_rewire', 'Full Rewire'),
        ('unpermitted_additions', 'Unpermitted Additions'),
        ('historic_home', 'Historic Home'),
    ]
    
    restricted_rehabs = models.JSONField(default=list, blank=True)
    specialty_rehab_avoidance = models.JSONField(default=list, blank=True)

    # Strict Requirements
    STRICT_REQUIREMENTS = [
        ('legal_access_required', 'Legal Access Required'),
        ('utilities_at_road', 'Utilities at Road'),
        ('no_flood_zone', 'No Flood Zone'),
        ('clear_title', 'Clear Title'),
        ('no_hoa', 'No HOA'),
        ('paved_road_access', 'Paved Road Access'),
        ('mobile_home_allowed', 'Mobile Home Allowed'),
    ]
    
    strict_requirements = models.JSONField(default=list, blank=True)

    # Location Characteristics
    LOCATION_CHARACTERISTICS = [
        ('flood_zone', 'Flood Zone'),
        ('near_main_road', 'Near Main Road'),
        ('hoa_community', 'HOA Community'),
        ('55_plus_community', '55+ Community'),
        ('near_commercial', 'Near Commercial'),
        ('waterfront', 'Waterfront'),
        ('near_railroad', 'Near Railroad'),
    ]
    
    location_characteristics = models.JSONField(default=list, blank=True)

    # Property Characteristics
    PROPERTY_CHARACTERISTICS = [
        ('pool', 'Pool'),
        ('garage', 'Garage'),
        ('solar_panels', 'Solar Panels'),
        ('wood_frame', 'Wood Frame'),
        ('driveway', 'Driveway'),
        ('city_water', 'City Water'),
        ('well_water', 'Well Water'),
        ('septic_tank', 'Septic Tank'),
        ('power_at_street', 'Power at Street'),
        ('perk_tested', 'Perk Tested'),
    ]
    
    property_characteristics = models.JSONField(default=list, blank=True)
    
    EXIT_STRATEGY_CHOICES = [
        ('infill', 'Infill Lot Development'),
        ('flip', 'Buy & Flip'),
        ('subdivide', 'Subdivide & Sell'),
        ('seller_financing', 'Seller Financing'),
        ('rezoning', 'Entitlement/Rezoning'),
        ('mobile_home', 'Mobile Home Lot'),
    ]
    
    exit_strategy = models.JSONField(default=list, blank=True)
    
    property_characteristics = models.JSONField(default=list, blank=True)

    # Internal notes
    notes = models.TextField(blank=True, null=True, help_text="Internal admin notes")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"BuyBox for {self.buyer.name}"
    
    
class BuyerDealLog(models.Model):
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("declined", "Declined"),
        ("offer_made", "Offer Made"),
        ("under_contract", "Under Contract"),
        ("accepted", "Accepted"),
    ]

    buyer = models.ForeignKey(BuyerProfile, on_delete=models.CASCADE, related_name="deal_logs")
    deal = models.ForeignKey(PropertySubmission, on_delete=models.CASCADE, related_name="buyer_logs")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="sent")
    sent_date = models.DateTimeField(auto_now_add=True)
    match_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    reject_note = models.TextField(null=True, blank=True) 
    class Meta:
        ordering = ["-sent_date"]

    def __str__(self):
        return f"{self.deal} -> {self.buyer} ({self.status})"