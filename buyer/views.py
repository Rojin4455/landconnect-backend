from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import BuyerProfile, BuyBoxFilter
from .serializers import BuyerProfileSerializer, BuyBoxFilterSerializer
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from data_management_app.models import PropertySubmission
from .utils import match_property_to_buyers, match_property_to_single_buyer
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404



class BuyerProfileCreateView(generics.CreateAPIView):
    queryset = BuyerProfile.objects.all()
    serializer_class = BuyerProfileSerializer
    permission_classes = [IsAuthenticated]
    
class BuyerProfileListView(generics.ListAPIView):
    queryset = BuyerProfile.objects.all()
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
            # Get all active properties
            active_properties = PropertySubmission.objects.select_related(
                "land_type", "utilities", "access_type"
            ).filter(status='submitted')
            
            matches = []
            
            for property_instance in active_properties:
                # Use the enhanced matching logic for one buyer
                match_result = match_property_to_single_buyer(property_instance, buybox_filter)
                
                if match_result:
                    matches.append({
                        "property_id": property_instance.id,
                        "property_address": property_instance.address,
                        "property_details": {
                            "land_type": property_instance.land_type.display_name if property_instance.land_type else None,
                            "acreage": float(property_instance.acreage),
                            "asking_price": float(property_instance.asking_price),
                            "zoning": property_instance.zoning,
                            "access_type": property_instance.access_type.display_name if property_instance.access_type else None,
                            "utilities": property_instance.utilities.display_name if property_instance.utilities else None,
                            "topography": property_instance.topography,
                            "environmental_factors": property_instance.environmental_factors,
                            "nearest_attraction": property_instance.nearest_attraction,
                            "property_characteristics": property_instance.property_characteristics,
                            "location_characteristics": property_instance.location_characteristics,
                        },
                        "match_score": match_result["match_score"],
                        "likelihood": match_result["likelihood"],
                        "factors_evaluated": match_result["factors_evaluated"],
                        "factors_matched": match_result["factors_matched"],
                        "match_details": match_result["match_details"]
                    })
            
            # Sort by match score (highest first)
            matches.sort(key=lambda x: x["match_score"], reverse=True)
            
            # Summary statistics
            total_matches = len(matches)
            high_likelihood = len([m for m in matches if m["likelihood"] == "High"])
            medium_likelihood = len([m for m in matches if m["likelihood"] == "Medium"])
            low_likelihood = len([m for m in matches if m["likelihood"] == "Low"])
            
            return {
                "buyer_id": buybox_filter.buyer.id,
                "buyer_name": buybox_filter.buyer.name,
                "total_properties_available": active_properties.count(),
                "total_matches": total_matches,
                "matches": matches[:20],  # Limit to top 20 matches for performance
                "match_summary": {
                    "high_likelihood": high_likelihood,
                    "medium_likelihood": medium_likelihood,
                    "low_likelihood": low_likelihood,
                },
                "matching_criteria_active": {
                    "asset_type": buybox_filter.asset_type,
                    "is_active_buyer": buybox_filter.is_active_buyer,
                    "is_blacklisted": buybox_filter.is_blacklisted,
                    "has_location_preferences": bool(
                        buybox_filter.preferred_cities or 
                        buybox_filter.preferred_counties or 
                        buybox_filter.preferred_states or
                        buybox_filter.preferred_zip_codes
                    ),
                    "has_price_range": bool(buybox_filter.price_min or buybox_filter.price_max),
                    "has_lot_size_range": bool(buybox_filter.lot_size_min or buybox_filter.lot_size_max),
                    "has_land_preferences": bool(buybox_filter.land_type or buybox_filter.access_type),
                    "has_strict_requirements": bool(buybox_filter.strict_requirements),
                }
            }
            
        except Exception as e:
            return {
                "error": f"Error calculating matches: {str(e)}",
                "buyer_id": buybox_filter.buyer.id,
                "total_matches": 0,
                "matches": [],
                "match_summary": {
                    "high_likelihood": 0,
                    "medium_likelihood": 0,
                    "low_likelihood": 0,
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
        
        matches = match_property_to_buyers(property_instance)
        
        # Return comprehensive admin data
        response_data = {
            "property_id": property_instance.id,
            "property_address": property_instance.address,
            "property_details": {
                "land_type": property_instance.land_type.display_name if property_instance.land_type else None,
                "acreage": float(property_instance.acreage),
                "asking_price": float(property_instance.asking_price),
                "zoning": property_instance.zoning,
                "access_type": property_instance.access_type.display_name if property_instance.access_type else None,
                "utilities": property_instance.utilities.display_name if property_instance.utilities else None,
            },
            "total_matches": len(matches),
            "matches": matches,
            "match_summary": {
                "high_likelihood": len([m for m in matches if m["likelihood"] == "High"]),
                "medium_likelihood": len([m for m in matches if m["likelihood"] == "Medium"]), 
                "low_likelihood": len([m for m in matches if m["likelihood"] == "Low"]),
            }
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
                "is_active": buybox_filter.is_active_buyer,
                "is_blacklisted": buybox_filter.is_blacklisted,
                "location_preferences": {
                    "cities": buybox_filter.preferred_cities,
                    "counties": buybox_filter.preferred_counties,
                    "states": buybox_filter.preferred_states,
                    "zip_codes": buybox_filter.preferred_zip_codes,
                },
                "investment_strategies": {
                    "house_strategies": buybox_filter.house_strategies,
                    "land_strategies": buybox_filter.land_strategies,
                },
                "property_types": {
                    "house_property_types": buybox_filter.house_property_types,
                    "land_property_types": buybox_filter.land_property_types,
                },
                "price_range": {
                    "min": buybox_filter.price_min,
                    "max": buybox_filter.price_max,
                },
                "lot_size_acres": {
                    "min": buybox_filter.lot_size_min,
                    "max": buybox_filter.lot_size_max,
                },
                "bedrooms_min": buybox_filter.bedroom_min,
                "bathrooms_min": buybox_filter.bathroom_min,
                "living_area_sqft": {
                    "min": buybox_filter.sqft_min,
                    "max": buybox_filter.sqft_max,
                },
                "year_built": {
                    "min": buybox_filter.year_built_min,
                    "max": buybox_filter.year_built_max,
                },
                "restricted_rehabs": buybox_filter.restricted_rehabs,
                "specialty_rehab_avoidance": buybox_filter.specialty_rehab_avoidance,
                "strict_requirements": buybox_filter.strict_requirements,
                "location_characteristics": buybox_filter.location_characteristics,
                "property_characteristics": buybox_filter.property_characteristics,
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

        recent_properties = PropertySubmission.objects.filter(
            created_at__gte=thirty_days_ago,
            status='submitted'
        )
        all_time_properties = PropertySubmission.objects.filter(status='submitted')

        recent_matches = []
        all_time_matches = []

        for prop in recent_properties:
            match_result = match_property_to_single_buyer(prop, buybox_filter)
            if match_result:
                recent_matches.append({
                    "property_id": prop.id,
                    "display_name": f"{prop.address} — {prop.land_type.display_name}",
                    "address": prop.address,
                    "land_type": prop.land_type.display_name,
                    "acreage": prop.acreage,
                    "asking_price": prop.asking_price,
                    "match_score": match_result["match_score"],
                    "likelihood": match_result["likelihood"],
                })
        for prop in all_time_properties:
            match_result = match_property_to_single_buyer(prop, buybox_filter)
            if match_result:
                all_time_matches.append({
                    "property_id": prop.id,
                    "display_name": f"{prop.address} — {prop.land_type.display_name}",
                    "address": prop.address,
                    "land_type": prop.land_type.display_name,
                    "acreage": prop.acreage,
                    "asking_price": prop.asking_price,
                    "match_score": match_result["match_score"],
                    "likelihood": match_result["likelihood"],
                })

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
            },
            "all_time_performance": {
                "total_properties": all_time_properties.count(),
                "total_matches": len(all_time_matches),
                "match_rate_percentage": round((len(all_time_matches) / all_time_properties.count() * 100) if all_time_properties.count() > 0 else 0, 2),
                "avg_match_score": round(sum(m['match_score'] for m in all_time_matches) / len(all_time_matches), 2) if all_time_matches else 0,
            },
            "likelihood_breakdown": {
                "high_likelihood_count": len([m for m in all_time_matches if m["likelihood"] == "High"]),
                "medium_likelihood_count": len([m for m in all_time_matches if m["likelihood"] == "Medium"]),
                "low_likelihood_count": len([m for m in all_time_matches if m["likelihood"] == "Low"]),
            }
        }

        return stats, recent_matches, all_time_matches


class PublicBuyBoxCriteriaListView(generics.ListAPIView):
    """
    Public API endpoint that returns only buy box criteria without buyer details.
    This is for displaying buyer criteria in the user-facing JV section.
    """
    queryset = BuyBoxFilter.objects.filter(
        is_active_buyer=True,  # Only show active buyers
        is_blacklisted=False   # Exclude blacklisted buyers
    ).select_related('buyer')
    
    serializer_class = BuyBoxFilterSerializer
    permission_classes = []  # No authentication required for public view
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Transform the data to show only criteria without buyer details
        public_criteria = []
        
        for buybox in queryset:
            criteria_data = {
                "id": buybox.id,  # Keep ID for potential future reference
                "asset_type": buybox.get_asset_type_display(),
                "asset_type_value": buybox.asset_type,
                
                # Location Preferences
                "location_preferences": {
                    "cities": buybox.preferred_cities,
                    "counties": buybox.preferred_counties,
                    "states": buybox.preferred_states,
                    "zip_codes": buybox.preferred_zip_codes,
                },
                
                # Investment Strategies
                "investment_strategies": {
                    "house_strategies": buybox.house_strategies,
                    "land_strategies": buybox.land_strategies,
                },
                
                # Property Types
                "property_types": {
                    "house_property_types": buybox.house_property_types,
                    "land_property_types": buybox.land_property_types,
                },
                
                # Price Range
                "price_range": {
                    "min": float(buybox.price_min) if buybox.price_min else None,
                    "max": float(buybox.price_max) if buybox.price_max else None,
                },
                
                # Lot Size (for land)
                "lot_size_range": {
                    "min": float(buybox.lot_size_min) if buybox.lot_size_min else None,
                    "max": float(buybox.lot_size_max) if buybox.lot_size_max else None,
                },
                
                # House-specific preferences
                "house_preferences": {
                    "bedroom_min": buybox.bedroom_min,
                    "bathroom_min": float(buybox.bathroom_min) if buybox.bathroom_min else None,
                    "sqft_min": buybox.sqft_min,
                    "sqft_max": buybox.sqft_max,
                    "year_built_min": buybox.year_built_min,
                    "year_built_max": buybox.year_built_max,
                },
                
                # Land-specific preferences
                "land_preferences": {
                    "land_type": buybox.land_type.display_name if buybox.land_type else None,
                    "access_type": buybox.access_type.display_name if buybox.access_type else None,
                    "preferred_utility": buybox.preferred_utility.name if buybox.preferred_utility else None,
                    "zoning": buybox.zoning,
                },
                
                # Rehab Restrictions
                "rehab_restrictions": {
                    "restricted_rehabs": buybox.restricted_rehabs,
                    "specialty_rehab_avoidance": buybox.specialty_rehab_avoidance,
                },
                
                # Requirements and Characteristics
                "requirements": {
                    "strict_requirements": buybox.strict_requirements,
                    "location_characteristics": buybox.location_characteristics,
                    "property_characteristics": buybox.property_characteristics,
                },
                
                # Metadata (without buyer info)
                "criteria_updated": buybox.updated_at.isoformat(),
            }
            
            public_criteria.append(criteria_data)
        
        response_data = {
            "total_active_buyers": len(public_criteria),
            "buy_box_criteria": public_criteria,
            "message": "Active buyer criteria for JV deal matching"
        }
        
        return Response(response_data, status=status.HTTP_200_OK)