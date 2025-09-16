from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import BuyerProfile, BuyBoxFilter, BuyerDealLog
from .serializers import BuyerProfileSerializer, BuyBoxFilterSerializer, BuyerDealLogSerializer, BuyerDealDetailSerializer
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from data_management_app.models import PropertySubmission
from .utils import match_property_to_buyers, match_property_to_single_buyer
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404
from ghl_accounts.utils import create_ghl_contact_for_buyer
from ghl_accounts.models import GHLAuthCredentials
import requests
import logging
from decouple import config
from .utils import update_buyer_deal_fields, update_buyer_deal_action


class BuyerProfileCreateView(generics.CreateAPIView):
    queryset = BuyerProfile.objects.all()
    serializer_class = BuyerProfileSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Save buyer locally first
        buyer = serializer.save()

        # Get latest GHL credentials
        creds = GHLAuthCredentials.objects.last()
        if not creds:
            raise Exception("No GHL credentials found in DB. Please authenticate first.")

        # Create GHL contact
        ghl_contact_id = create_ghl_contact_for_buyer(
            creds.access_token,
            creds.location_id,
            buyer
        )

        # Update buyer with GHL contact ID
        if ghl_contact_id:
            buyer.ghl_contact_id = ghl_contact_id
            buyer.save(update_fields=["ghl_contact_id"])

        # Return buyer for re-serialization
        self._buyer = buyer

    def create(self, request, *args, **kwargs):
        # Run parent logic (this calls perform_create)
        super().create(request, *args, **kwargs)

        # Re-serialize updated buyer (with ghl_contact_id)
        serializer = self.get_serializer(self._buyer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
class BuyerProfileListView(generics.ListAPIView):
    queryset = BuyerProfile.objects.all().order_by('-created_at')
    serializer_class = BuyerProfileSerializer
    permission_classes = [IsAuthenticated]
    
class BuyerProfileDetailView(generics.RetrieveUpdateAPIView):
    queryset = BuyerProfile.objects.all()
    serializer_class = BuyerProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'buyer_id'

    def get_object(self):
        return generics.get_object_or_404(BuyerProfile, id=self.kwargs['buyer_id'])
    
class BuyerProfileDeleteView(generics.DestroyAPIView):
    queryset = BuyerProfile.objects.all()
    serializer_class = BuyerProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "buyer_id"

    def perform_destroy(self, instance):
        if instance.ghl_contact_id:
            creds = GHLAuthCredentials.objects.last()
            if creds:
                url = f"https://services.leadconnectorhq.com/contacts/{instance.ghl_contact_id}"
                headers = {
                    "Authorization": f"Bearer {creds.access_token}",
                    "Accept": "application/json",
                    "Version": "2021-07-28"
                }

                response = requests.delete(url, headers=headers)

                if response.status_code not in [200, 204]:
                    # Optional: raise an error or just ignore
                    pass

        super().perform_destroy(instance)
    
    
class BuyBoxFilterUpsertView(generics.RetrieveUpdateAPIView):
    serializer_class = BuyBoxFilterSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        buyer_id = self.kwargs.get('buyer_id')
        try:
            buyer = BuyerProfile.objects.get(id=buyer_id)
        except BuyerProfile.DoesNotExist:
            raise NotFound("BuyerProfile not found.")

        obj, _ = BuyBoxFilter.objects.get_or_create(buyer=buyer)
        return obj

    def retrieve(self, request, *args, **kwargs):
        """GET - Retrieve buybox with matching results"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Get matching results
        matching_results = self.get_matching_results(instance)
        
        response_data = {
            'buybox_criteria': serializer.data,
            'matching_results': matching_results
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """PUT/PATCH - Update buybox and return matching results"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            serializer.save()
            
            # Get matching results after update
            matching_results = self.get_matching_results(instance)
            
            response_data = {
                'buybox_criteria': serializer.data,
                'matching_results': matching_results,
                'message': 'BuyBox criteria updated successfully'
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_matching_results(self, buybox_filter):
        """Get comprehensive matching results for this buyer"""
        try:
            # Get all active properties - only submitted status
            active_properties = PropertySubmission.objects.select_related(
                "land_type", "utilities", "access_type"
            ).filter(status='submitted')
            
            matches = []
            
            for property_instance in active_properties:
                # Use the enhanced matching logic for one buyer
                match_result = match_property_to_single_buyer(property_instance, buybox_filter)
                
                if match_result:
                    # Convert lot_size to acres if needed for display
                    display_lot_size = property_instance.lot_size
                    if property_instance.lot_size_unit == 'sqft':
                        display_lot_size = float(property_instance.lot_size) / 43560
                    
                    matches.append({
                        "property_id": property_instance.id,
                        "property_address": property_instance.address,
                        "property_details": {
                            "land_type": property_instance.land_type.display_name if property_instance.land_type else None,
                            "lot_size": float(display_lot_size),
                            "lot_size_unit": "acres",  # Standardize to acres for display
                            "agreed_price": float(property_instance.agreed_price),
                            "exit_strategy": property_instance.exit_strategy,
                            "exit_strategy_display": property_instance.get_exit_strategy_display(),
                            "zoning": property_instance.zoning,
                            "access_type": property_instance.access_type.display_name if property_instance.access_type else None,
                            "utilities": property_instance.utilities.display_name if property_instance.utilities else None,
                            "property_characteristics": property_instance.property_characteristics,
                            "location_characteristics": property_instance.location_characteristics,
                        },
                        "match_score": match_result["match_score"],
                        "likelihood": match_result["likelihood"],
                        "component_scores": match_result["component_scores"],
                        "weighted_contribution": match_result["weighted_contribution"],
                        "match_details": match_result["match_details"]
                    })
            
            # Sort by match score (highest first)
            matches.sort(key=lambda x: x["match_score"], reverse=True)
            
            # Categorize matches using the correct categories from utils
            good_fit = len([m for m in matches if m["likelihood"] == "Good Fit"])
            marginal_fit = len([m for m in matches if m["likelihood"] == "Marginal Fit"])
            poor_fit = len([m for m in matches if m["likelihood"] == "Poor Fit"])
            
            return {
                "buyer_id": buybox_filter.buyer.id,
                "buyer_name": buybox_filter.buyer.name,
                "total_properties_available": active_properties.count(),
                "total_matches": len(matches),
                "matches": matches[:20],  # Limit to top 20 matches for performance
                "match_summary": {
                    "good_fit": good_fit,
                    "marginal_fit": marginal_fit, 
                    "poor_fit": poor_fit,
                },
                "matching_criteria_active": {
                    "asset_type": buybox_filter.asset_type,
                    "is_active_buyer": buybox_filter.is_active_buyer,
                    "is_blacklisted": buybox_filter.is_blacklisted,
                    "has_location_preferences": bool(buybox_filter.address),
                    "has_price_range": bool(buybox_filter.price_min or buybox_filter.price_max),
                    "has_lot_size_range": bool(buybox_filter.lot_size_min or buybox_filter.lot_size_max),
                    "has_land_preferences": bool(buybox_filter.land_type or buybox_filter.access_type),
                    "has_exit_strategies": bool(buybox_filter.land_strategies),
                }
            }
            
        except Exception as e:
            return {
                "error": f"Error calculating matches: {str(e)}",
                "buyer_id": buybox_filter.buyer.id,
                "total_matches": 0,
                "matches": [],
                "match_summary": {
                    "good_fit": 0,
                    "marginal_fit": 0,
                    "poor_fit": 0,
                }
            }


class MatchPropertyToBuyersView(APIView):
    """Enhanced property matching view with comprehensive logic"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        try:
            property_instance = PropertySubmission.objects.select_related(
                "land_type", "utilities", "access_type"
            ).get(pk=pk)
        except PropertySubmission.DoesNotExist:
            return Response({"detail": "Property not found."}, status=404)
        
        # Use the comprehensive matching function from utils
        match_results = match_property_to_buyers(property_instance)
        
        # Convert lot_size to acres if needed for display
        display_lot_size = property_instance.lot_size
        if property_instance.lot_size_unit == 'sqft':
            display_lot_size = float(property_instance.lot_size) / 43560
        
        # Return comprehensive admin data with the correct structure from utils
        response_data = {
            "property_id": property_instance.id,
            "property_address": property_instance.address,
            "property_details": {
                "land_type": property_instance.land_type.display_name if property_instance.land_type else None,
                "lot_size": float(display_lot_size),
                "lot_size_unit": "acres",  # Standardize to acres
                "agreed_price": float(property_instance.agreed_price),
                "exit_strategy": property_instance.exit_strategy,
                "exit_strategy_display": property_instance.get_exit_strategy_display(),
                "zoning": property_instance.zoning,
                "access_type": property_instance.access_type.display_name if property_instance.access_type else None,
                "utilities": property_instance.utilities.display_name if property_instance.utilities else None,
                "property_characteristics": property_instance.property_characteristics,
                "location_characteristics": property_instance.location_characteristics,
            },
            "matching_results": match_results
        }
        
        return Response(response_data, status=200)


class BuyerMatchingStatsView(APIView):
    """
    Admin view:
    Tab 1 → Buyer Profile (editable)
    Tab 2 → Buy Box Criteria (editable)
    Tab 3 → Matching Results (stats + matching properties)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, buyer_id):
        buyer = get_object_or_404(BuyerProfile, id=buyer_id)
        buybox_filter = get_object_or_404(BuyBoxFilter, buyer=buyer)

        stats, recent_matches, all_time_matches = self.calculate_buyer_stats(buybox_filter)

        return Response({
            "buyer_profile": {
                "id": buyer.id,
                "name": buyer.name,
                "email": buyer.email,
                "phone": buyer.phone,
                "created_at": buyer.created_at,
                "updated_at": buyer.updated_at,
            },
            "buybox_criteria": {
                "asset_type": buybox_filter.asset_type,
                "asset_type_display": buybox_filter.get_asset_type_display(),
                "is_active": buybox_filter.is_active_buyer,
                "is_blacklisted": buybox_filter.is_blacklisted,
                "address": buybox_filter.address,
                "investment_strategies": {
                    "house_strategies": buybox_filter.house_strategies,
                    "land_strategies": buybox_filter.land_strategies,
                },
                "property_types": {
                    "house_property_types": buybox_filter.house_property_types,
                    "land_property_types": buybox_filter.land_property_types,
                },
                "price_range": {
                    "min": float(buybox_filter.price_min) if buybox_filter.price_min else None,
                    "max": float(buybox_filter.price_max) if buybox_filter.price_max else None,
                },
                "lot_size_acres": {
                    "min": float(buybox_filter.lot_size_min) if buybox_filter.lot_size_min else None,
                    "max": float(buybox_filter.lot_size_max) if buybox_filter.lot_size_max else None,
                },
                "land_preferences": {
                    "land_property_types": buybox_filter.land_property_types,  # JSONField list
                    "access_type": buybox_filter.access_type.display_name if buybox_filter.access_type else None,
                    "preferred_utility": buybox_filter.preferred_utility.name if buybox_filter.preferred_utility else None,
                    "zoning": buybox_filter.zoning,
                },
                "house_preferences": {
                    "bedrooms_min": buybox_filter.bedroom_min,
                    "bathrooms_min": float(buybox_filter.bathroom_min) if buybox_filter.bathroom_min else None,
                    "living_area_sqft": {
                        "min": buybox_filter.sqft_min,
                        "max": buybox_filter.sqft_max,
                    },
                    "year_built": {
                        "min": buybox_filter.year_built_min,
                        "max": buybox_filter.year_built_max,
                    },
                },
                "restrictions": {
                    "restricted_rehabs": buybox_filter.restricted_rehabs,
                    "specialty_rehab_avoidance": buybox_filter.specialty_rehab_avoidance,
                    "strict_requirements": buybox_filter.strict_requirements,
                },
                "characteristics": {
                    "location_characteristics": buybox_filter.location_characteristics,
                    "property_characteristics": buybox_filter.property_characteristics,
                },
                "exit_strategies": buybox_filter.exit_strategy,  # JSONField for exit strategies
                "notes": buybox_filter.notes,
            },

            "matching_stats": stats,
            "matching_results": {
                "recent_matches": recent_matches,
                "all_time_matches": all_time_matches,
            }
        }, status=200)

    def calculate_buyer_stats(self, buybox_filter):
        """Calculate buyer matching statistics & return matching property details"""
        thirty_days_ago = datetime.now() - timedelta(days=30)

        recent_properties = PropertySubmission.objects.select_related(
            "land_type", "utilities", "access_type"
        ).filter(
            created_at__gte=thirty_days_ago,
            status='submitted'
        )
        
        all_time_properties = PropertySubmission.objects.select_related(
            "land_type", "utilities", "access_type"
        ).filter(status='submitted')

        recent_matches = []
        all_time_matches = []

        for prop in recent_properties:
            match_result = match_property_to_single_buyer(prop, buybox_filter)
            if match_result:
                # Convert lot_size to acres for display
                display_lot_size = prop.lot_size
                if prop.lot_size_unit == 'sqft':
                    display_lot_size = float(prop.lot_size) / 43560
                    
                recent_matches.append({
                    "property_id": prop.id,
                    "display_name": f"{prop.address} — {prop.land_type.display_name if prop.land_type else 'Unknown'}",
                    "address": prop.address,
                    "land_type": prop.land_type.display_name if prop.land_type else None,
                    "lot_size": float(display_lot_size),
                    "lot_size_unit": "acres",
                    "agreed_price": float(prop.agreed_price),
                    "exit_strategy": prop.exit_strategy,
                    "exit_strategy_display": prop.get_exit_strategy_display(),
                    "match_score": match_result["match_score"],
                    "likelihood": match_result["likelihood"],
                    "created_at": prop.created_at.isoformat(),
                })
        
        for prop in all_time_properties:
            match_result = match_property_to_single_buyer(prop, buybox_filter)
            if match_result:
                # Convert lot_size to acres for display
                display_lot_size = prop.lot_size
                if prop.lot_size_unit == 'sqft':
                    display_lot_size = float(prop.lot_size) / 43560
                    
                all_time_matches.append({
                    "property_id": prop.id,
                    "display_name": f"{prop.address} — {prop.land_type.display_name if prop.land_type else 'Unknown'}",
                    "address": prop.address,
                    "land_type": prop.land_type.display_name if prop.land_type else None,
                    "lot_size": float(display_lot_size),
                    "lot_size_unit": "acres",
                    "agreed_price": float(prop.agreed_price),
                    "exit_strategy": prop.exit_strategy,
                    "exit_strategy_display": prop.get_exit_strategy_display(),
                    "match_score": match_result["match_score"],
                    "likelihood": match_result["likelihood"],
                    "created_at": prop.created_at.isoformat(),
                })

        # Sort matches by score (highest first)
        recent_matches.sort(key=lambda x: x["match_score"], reverse=True)
        all_time_matches.sort(key=lambda x: x["match_score"], reverse=True)

        # Updated to use the correct likelihood categories from documentation
        good_fit_recent = [m for m in recent_matches if m["match_score"] > 45]
        marginal_fit_recent = [m for m in recent_matches if 40 <= m["match_score"] <= 45]
        poor_fit_recent = [m for m in recent_matches if m["match_score"] < 40]
        
        good_fit_all = [m for m in all_time_matches if m["match_score"] > 45]
        marginal_fit_all = [m for m in all_time_matches if 40 <= m["match_score"] <= 45]
        poor_fit_all = [m for m in all_time_matches if m["match_score"] < 40]

        stats = {
            "buyer_id": buybox_filter.buyer.id,
            "buyer_name": buybox_filter.buyer.name,
            "buybox_status": {
                "is_active": buybox_filter.is_active_buyer,
                "is_blacklisted": buybox_filter.is_blacklisted,
                "asset_type": buybox_filter.get_asset_type_display(),
            },
            "recent_performance": {
                "total_properties_last_30_days": recent_properties.count(),
                "total_matches_last_30_days": len(recent_matches),
                "match_rate_percentage": round((len(recent_matches) / recent_properties.count() * 100) if recent_properties.count() > 0 else 0, 2),
                "avg_match_score": round(sum(m['match_score'] for m in recent_matches) / len(recent_matches), 2) if recent_matches else 0,
                "good_fit_count": len(good_fit_recent),
                "marginal_fit_count": len(marginal_fit_recent), 
                "poor_fit_count": len(poor_fit_recent),
            },
            "all_time_performance": {
                "total_properties": all_time_properties.count(),
                "total_matches": len(all_time_matches),
                "match_rate_percentage": round((len(all_time_matches) / all_time_properties.count() * 100) if all_time_properties.count() > 0 else 0, 2),
                "avg_match_score": round(sum(m['match_score'] for m in all_time_matches) / len(all_time_matches), 2) if all_time_matches else 0,
                "good_fit_count": len(good_fit_all),
                "marginal_fit_count": len(marginal_fit_all),
                "poor_fit_count": len(poor_fit_all),
            },
            "likelihood_breakdown": {
                "good_fit_count": len(good_fit_all),
                "marginal_fit_count": len(marginal_fit_all),
                "poor_fit_count": len(poor_fit_all),
            }
        }

        return stats, recent_matches[:50], all_time_matches[:100]  # Limit results for performance


class PublicBuyBoxCriteriaListView(generics.ListAPIView):
    """
    Public API endpoint that returns only buy box criteria without buyer details.
    This is for displaying buyer criteria in the user-facing JV section.
    Enhanced with proper field mapping and choice display names.
    """
    serializer_class = BuyBoxFilterSerializer
    permission_classes = []  # No authentication required for public view
    
    def get_queryset(self):
        return BuyBoxFilter.objects.filter(
            is_active_buyer=True,  # Only show active buyers
            is_blacklisted=False,   # Exclude blacklisted buyers
            asset_type__in=['land', 'both']  # Only show buyers who buy land
        ).select_related('buyer', 'access_type', 'preferred_utility')
    
    def get_choice_display_name(self, choices_dict, value):
        """Helper method to get display name for choice fields"""
        return choices_dict.get(value, value) if value else None
    
    def get_multiple_choice_display_names(self, choices_dict, values_list):
        """Helper method to get display names for multiple choice fields (JSONField lists)"""
        if not values_list:
            return []
        
        display_names = []
        for value in values_list:
            display_name = choices_dict.get(value, value)
            display_names.append(display_name)
        return display_names
    
    def get_multiple_choice_with_values(self, choices_dict, values_list):
        """Helper method that returns both value and display for advanced frontends"""
        if not values_list:
            return []
        
        result = []
        for value in values_list:
            display_name = choices_dict.get(value, value)
            result.append({
                "value": value,
                "display": display_name
            })
        return result
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Choice mappings from your model
        LAND_STRATEGY_CHOICES_DICT = {
            'infill_development': 'Infill Lot Development',
            'buy_flip': 'Buy & Flip',
            'buy_hold': 'Buy & Hold',
            'subdivide_sell': 'Subdivide & Sell',
            'seller_financing': 'Seller Financing',
            'rv_lot': 'RV Lot / Tiny Home Lot / Mobile Home Lot',
            'entitlement': 'Entitlement / Rezoning',
        }
        
        LAND_PROPERTY_TYPES_DICT = {
            'residential_vacant': 'Residential Vacant',
            'agricultural': 'Agricultural',
            'commercial': 'Commercial',
            'recreational': 'Recreational',
            'timberland': 'Timberland / Hunting',
            'waterfront': 'Waterfront',
            'subdividable': 'Subdividable',
        }
        
        EXIT_STRATEGY_CHOICES_DICT = {
            'infill': 'Infill Lot Development',
            'flip': 'Buy & Flip',
            'subdivide': 'Subdivide & Sell',
            'seller_financing': 'Seller Financing',
            'rezoning': 'Entitlement/Rezoning',
            'mobile_home': 'Mobile Home Lot',
        }
        
        STRICT_REQUIREMENTS_DICT = {
            'legal_access_required': 'Legal Access Required',
            'utilities_at_road': 'Utilities at Road',
            'no_flood_zone': 'No Flood Zone',
            'clear_title': 'Clear Title',
            'no_hoa': 'No HOA',
            'paved_road_access': 'Paved Road Access',
            'mobile_home_allowed': 'Mobile Home Allowed',
        }
        
        LOCATION_CHARACTERISTICS_DICT = {
            'flood_zone': 'Flood Zone',
            'near_main_road': 'Near Main Road',
            'hoa_community': 'HOA Community',
            '55_plus_community': '55+ Community',
            'near_commercial': 'Near Commercial',
            'waterfront': 'Waterfront',
            'near_railroad': 'Near Railroad',
        }
        
        PROPERTY_CHARACTERISTICS_DICT = {
            'pool': 'Pool',
            'garage': 'Garage',
            'solar_panels': 'Solar Panels',
            'wood_frame': 'Wood Frame',
            'driveway': 'Driveway',
            'city_water': 'City Water',
            'well_water': 'Well Water',
            'septic_tank': 'Septic Tank',
            'power_at_street': 'Power at Street',
            'perk_tested': 'Perk Tested',
        }
        
        # Transform the data to show only criteria without buyer details
        public_criteria = []
        
        for buybox in queryset:
            criteria_data = {
                "id": buybox.id,  # Keep ID for potential future reference
                "asset_type": buybox.get_asset_type_display(),
                
                # Location Preference
                "location_preferences": buybox.address or "No specific location preference",
                
                # Investment Strategies (properly mapped from land_strategies field)
                "investment_strategies": self.get_multiple_choice_display_names(
                    LAND_STRATEGY_CHOICES_DICT, 
                    buybox.land_strategies or []
                ),
                
                # Property Types (properly mapped from land_property_types field)
                "property_types": self.get_multiple_choice_display_names(
                    LAND_PROPERTY_TYPES_DICT,
                    buybox.land_property_types or []
                ),
                
                # Exit Strategies (properly mapped from exit_strategy field)
                "exit_strategies": self.get_multiple_choice_display_names(
                    EXIT_STRATEGY_CHOICES_DICT,
                    buybox.exit_strategy or []
                ),
                
                # Price Range
                "price_range": {
                    "min": float(buybox.price_min) if buybox.price_min else None,
                    "max": float(buybox.price_max) if buybox.price_max else None,
                    "formatted": self.format_price_range(buybox.price_min, buybox.price_max)
                },
                
                # Lot Size (for land) - in acres
                "lot_size_range": {
                    "min": float(buybox.lot_size_min) if buybox.lot_size_min else None,
                    "max": float(buybox.lot_size_max) if buybox.lot_size_max else None,
                    "unit": "acres",
                    "formatted": self.format_lot_size_range(buybox.lot_size_min, buybox.lot_size_max)
                },
                
                # Land-specific preferences (corrected field references)
                "land_preferences": {
                    "access_type": buybox.access_type.display_name if buybox.access_type else None,
                    "preferred_utility": buybox.preferred_utility.name if buybox.preferred_utility else None,
                    "zoning": buybox.zoning if buybox.zoning else [],
                },
                
                # Requirements and Characteristics with proper display names
                "requirements": {
                    "strict_requirements": self.get_multiple_choice_display_names(
                        STRICT_REQUIREMENTS_DICT,
                        buybox.strict_requirements or []
                    ),
                    "location_characteristics": self.get_multiple_choice_display_names(
                        LOCATION_CHARACTERISTICS_DICT,
                        buybox.location_characteristics or []
                    ),
                    "property_characteristics": self.get_multiple_choice_display_names(
                        PROPERTY_CHARACTERISTICS_DICT,
                        buybox.property_characteristics or []
                    ),
                },
                
                # Summary for easy display
                "summary": {
                    "asset_types": buybox.get_asset_type_display(),
                    "strategies_count": len(buybox.land_strategies or []) + len(buybox.exit_strategy or []),
                    "has_location_preference": bool(buybox.address),
                    "has_price_range": bool(buybox.price_min or buybox.price_max),
                    "has_lot_size_preference": bool(buybox.lot_size_min or buybox.lot_size_max),
                    "total_requirements": (
                        len(buybox.strict_requirements or []) + 
                        len(buybox.location_characteristics or []) + 
                        len(buybox.property_characteristics or [])
                    )
                },
                
                # Metadata (without buyer info)
                "criteria_last_updated": buybox.updated_at.isoformat(),
                "criteria_created": buybox.created_at.isoformat(),
            }
            
            public_criteria.append(criteria_data)
        
        # Sort by most recently updated first
        public_criteria.sort(key=lambda x: x["criteria_last_updated"], reverse=True)
        
        response_data = {
            "total_active_buyers": len(public_criteria),
            "buy_box_criteria": public_criteria,
            "summary_stats": {
                "buyers_wanting_land_only": len([c for c in public_criteria if c["asset_type"] == "Land"]),
                "buyers_wanting_both": len([c for c in public_criteria if c["asset_type"] == "Both"]),
                "buyers_with_location_preference": len([c for c in public_criteria if c["summary"]["has_location_preference"]]),
                "buyers_with_price_range": len([c for c in public_criteria if c["summary"]["has_price_range"]]),
                "avg_strategies_per_buyer": round(sum(c["summary"]["strategies_count"] for c in public_criteria) / len(public_criteria), 1) if public_criteria else 0,
            },
            "message": "Active buyer criteria for land deal matching"
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def format_price_range(self, min_price, max_price):
        """Format price range for display"""
        if not min_price and not max_price:
            return "No price limit specified"
        elif min_price and not max_price:
            return f"${int(min_price):,}+"
        elif not min_price and max_price:
            return f"Up to ${int(max_price):,}"
        else:
            return f"${int(min_price):,} - ${int(max_price):,}"
    
    def format_lot_size_range(self, min_size, max_size):
        """Format lot size range for display"""
        if not min_size and not max_size:
            return "No size preference specified"
        elif min_size and not max_size:
            return f"{float(min_size):g}+ acres"
        elif not min_size and max_size:
            return f"Up to {float(max_size):g} acres"
        else:
            return f"{float(min_size):g} - {float(max_size):g} acres"
        
class BuyBoxToggleActiveView(generics.UpdateAPIView):
    """
    Toggle the is_active_buyer flag for a buyer's BuyBox.
    """
    serializer_class = BuyBoxFilterSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "buyer_id"

    def get_object(self):
        buyer_id = self.kwargs.get("buyer_id")
        try:
            buyer = BuyerProfile.objects.get(id=buyer_id)
        except BuyerProfile.DoesNotExist:
            raise NotFound("BuyerProfile not found.")

        obj, _ = BuyBoxFilter.objects.get_or_create(buyer=buyer)
        return obj

    def patch(self, request, *args, **kwargs):
        buybox = self.get_object()

        # Flip the flag (toggle)
        buybox.is_active_buyer = not buybox.is_active_buyer
        buybox.save(update_fields=["is_active_buyer", "updated_at"])

        return Response(
            {
                "buyer_id": buybox.buyer.id,
                "buyer_name": buybox.buyer.name,
                "is_active_buyer": buybox.is_active_buyer,
                "message": "BuyBox active status updated successfully",
            },
            status=status.HTTP_200_OK,
        )


logger = logging.getLogger(__name__)

# Load from .env
FRONTEND_BASE_URI = config("FRONTEND_BASE_URI")
logger = logging.getLogger(__name__)


class BuyerDealLogCreateView(generics.CreateAPIView):
    queryset = BuyerDealLog.objects.all()
    serializer_class = BuyerDealLogSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        buyer_deal_log = serializer.save()
        print("🚀 BuyerDealLog created:", buyer_deal_log.id)

        try:
            deal_url = f"{FRONTEND_BASE_URI}/buyer/{buyer_deal_log.buyer.id}/deals"
            deal_address = buyer_deal_log.deal.address if buyer_deal_log.deal else ""
            deal_status = buyer_deal_log.status

            print("📌 Deal Info:", deal_url, deal_address, deal_status)

            if buyer_deal_log.buyer and getattr(buyer_deal_log.buyer, "ghl_contact_id", None):
                print(f"🔗 Updating GHL contact: {buyer_deal_log.buyer.ghl_contact_id}")
                update_buyer_deal_fields(
                    ghl_contact_id=buyer_deal_log.buyer.ghl_contact_id,
                    deal_url=deal_url,
                    deal_address=deal_address,
                    deal_status=deal_status
                )
            else:
                print("⚠️ Buyer missing GHL contact ID, skipping GHL update.")

        except Exception as e:
            print(f"❌ Error updating GHL custom fields: {e}")

    
class BuyerDealLogListView(generics.ListAPIView):
    serializer_class = BuyerDealLogSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        buyer_id = self.kwargs["buyer_id"]
        return BuyerDealLog.objects.filter(buyer_id=buyer_id)
    
class BuyerDealDetailView(generics.RetrieveAPIView):
    queryset = BuyerDealLog.objects.select_related("deal", "buyer")
    serializer_class = BuyerDealDetailSerializer
    permission_classes = [AllowAny]


class BuyerDealResponseView(generics.UpdateAPIView):
    queryset = BuyerDealLog.objects.all()
    serializer_class = BuyerDealLogSerializer
    permission_classes = [AllowAny]

    def update(self, request, *args, **kwargs):
        deal_log = self.get_object()
        action = request.data.get("action")
        reject_note = request.data.get("reject_note")  # optional note

        if action == "accept":
            deal_log.status = "accepted"
            deal_log.reject_note = None
        elif action == "reject":
            deal_log.status = "declined"
            deal_log.reject_note = reject_note or "Buyer declined the deal"
        else:
            return Response({"error": "Invalid action"}, status=400)

        deal_log.save()

        # Update GHL custom fields
        if deal_log.buyer and getattr(deal_log.buyer, "ghl_contact_id", None):
            update_buyer_deal_action(
                ghl_contact_id=deal_log.buyer.ghl_contact_id,
                deal_status=deal_log.status,
                reject_note=deal_log.reject_note
            )
        else:
            print("⚠️ Buyer missing GHL contact ID, skipping GHL update.")

        return Response(BuyerDealLogSerializer(deal_log).data)


