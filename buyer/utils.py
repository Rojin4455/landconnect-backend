from .models import BuyBoxFilter

def match_property_to_single_buyer(property_instance, buyer_filter):
    """
    Enhanced matching logic for a single buyer against a property
    Returns match result or None if no match
    """
    # Skip if buyer is inactive or blacklisted
    if not buyer_filter.is_active_buyer or buyer_filter.is_blacklisted:
        return None
    
    # Asset Type Check (CRITICAL - if they don't buy this asset type, skip)
    if buyer_filter.asset_type not in ['land', 'houses', 'both']:
        return None  # Skip this buyer - they don't buy land
    
    score = 0
    total_factors = 0
    match_details = {}
    
    # 1. Land Type Match (High Priority)
    if buyer_filter.land_type:
        total_factors += 2  # Higher weight for land type
        if buyer_filter.land_type == property_instance.land_type:
            score += 2
            match_details['land_type'] = 'Perfect Match'
        else:
            match_details['land_type'] = 'Mismatch'
    
    # 2. Lot Size Range (High Priority)
    if buyer_filter.lot_size_min is not None or buyer_filter.lot_size_max is not None:
        total_factors += 2  # Higher weight
        lot_size_min = buyer_filter.lot_size_min or 0
        lot_size_max = buyer_filter.lot_size_max or float('inf')
        if lot_size_min <= property_instance.acreage <= lot_size_max:
            score += 2
            match_details['lot_size'] = f'Within Range ({lot_size_min}-{lot_size_max} acres)'
        else:
            match_details['lot_size'] = f'Out of Range (Property: {property_instance.acreage} acres)'
    
    # 3. Price Range (Critical Factor)
    if buyer_filter.price_min is not None or buyer_filter.price_max is not None:
        total_factors += 3  # Highest weight for price
        price_min = buyer_filter.price_min or 0
        price_max = buyer_filter.price_max or float('inf')
        if price_min <= property_instance.asking_price <= price_max:
            score += 3
            match_details['price'] = f'Within Budget (${price_min:,} - ${price_max:,})'
        else:
            match_details['price'] = f'Out of Budget (Property: ${property_instance.asking_price:,})'
    
    # 4. Access Type
    if buyer_filter.access_type:
        total_factors += 1
        if buyer_filter.access_type == property_instance.access_type:
            score += 1
            match_details['access_type'] = 'Perfect Match'
        else:
            match_details['access_type'] = 'Different Access Type'
    
    # 5. Utilities Match
    if buyer_filter.preferred_utility:
        total_factors += 1
        if buyer_filter.preferred_utility == property_instance.utilities:
            score += 1
            match_details['utilities'] = 'Preferred Utility Match'
        else:
            match_details['utilities'] = 'Different Utility Type'
    
    # 6. Zoning Preferences
    if buyer_filter.zoning and property_instance.zoning:
        total_factors += 1
        zoning_match = False
        for preferred_zoning in buyer_filter.zoning:
            if preferred_zoning.lower() in property_instance.zoning.lower():
                zoning_match = True
                break
        if zoning_match:
            score += 1
            match_details['zoning'] = 'Acceptable Zoning'
        else:
            match_details['zoning'] = 'Zoning Mismatch'
    
    # 7. Location Preferences
    location_factors = 0
    location_score = 0
    location_matches = []
    
    # Check if property has location data (you might need to add these fields to PropertySubmission)
    property_city = getattr(property_instance, 'city', None)
    property_county = getattr(property_instance, 'county', None)
    property_state = getattr(property_instance, 'state', None)
    property_zip = getattr(property_instance, 'zip_code', None)
    
    # City preferences
    if buyer_filter.preferred_cities and property_city:
        location_factors += 1
        if property_city.lower() in [city.lower() for city in buyer_filter.preferred_cities]:
            location_score += 1
            location_matches.append('City')
    
    # County preferences  
    if buyer_filter.preferred_counties and property_county:
        location_factors += 1
        if property_county.lower() in [county.lower() for county in buyer_filter.preferred_counties]:
            location_score += 1
            location_matches.append('County')
            
    # State preferences
    if buyer_filter.preferred_states and property_state:
        location_factors += 1
        if property_state.upper() in [state.upper() for state in buyer_filter.preferred_states]:
            location_score += 1
            location_matches.append('State')
    
    # ZIP preferences
    if buyer_filter.preferred_zip_codes and property_zip:
        location_factors += 1
        if property_zip in buyer_filter.preferred_zip_codes:
            location_score += 1
            location_matches.append('ZIP')
    
    if location_factors > 0:
        total_factors += 2  # Location gets higher weight
        if location_score > 0:
            score += 2
            match_details['location'] = f"Matches: {', '.join(location_matches)}"
        else:
            match_details['location'] = 'No Location Match'
    
    # 8. Property Characteristics Match
    if buyer_filter.property_characteristics and property_instance.property_characteristics:
        total_factors += 1
        characteristic_matches = 0
        total_desired_characteristics = len(buyer_filter.property_characteristics)
        
        for desired_char in buyer_filter.property_characteristics:
            if desired_char in property_instance.property_characteristics:
                characteristic_matches += 1
        
        if characteristic_matches > 0:
            char_score = characteristic_matches / total_desired_characteristics
            score += char_score
            match_details['property_characteristics'] = f'{characteristic_matches}/{total_desired_characteristics} characteristics match'
        else:
            match_details['property_characteristics'] = 'No characteristic matches'
    
    # 9. Location Characteristics Match
    if buyer_filter.location_characteristics and property_instance.location_characteristics:
        total_factors += 1
        location_char_matches = 0
        total_desired_location_chars = len(buyer_filter.location_characteristics)
        
        for desired_char in buyer_filter.location_characteristics:
            if desired_char in property_instance.location_characteristics:
                location_char_matches += 1
        
        if location_char_matches > 0:
            loc_char_score = location_char_matches / total_desired_location_chars
            score += loc_char_score
            match_details['location_characteristics'] = f'{location_char_matches}/{total_desired_location_chars} location characteristics match'
        else:
            match_details['location_characteristics'] = 'No location characteristic matches'
    
    # 10. Strict Requirements Check (CRITICAL - any failure means no match)
    if buyer_filter.strict_requirements:
        for requirement in buyer_filter.strict_requirements:
            requirement_met = check_strict_requirement(property_instance, requirement)
            if not requirement_met:
                # Strict requirement not met - this is a deal breaker
                return None
        match_details['strict_requirements'] = 'All strict requirements met'
    
    # Calculate percentage (avoid division by zero)
    if total_factors == 0:
        return None  # Skip if no factors to evaluate
        
    percentage = (score / total_factors) * 100
    
    # Determine likelihood with enhanced logic
    if percentage >= 85:
        likelihood = "High"
    elif percentage >= 65:
        likelihood = "Medium"
    elif percentage >= 40:
        likelihood = "Low"
    else:
        return None  # Too low to be considered a match
    
    return {
        "match_score": round(percentage, 2),
        "likelihood": likelihood,
        "factors_evaluated": total_factors,
        "factors_matched": round(score, 2),
        "match_details": match_details
    }


def match_property_to_buyers(property_instance):
    """
    Enhanced matching logic that considers comprehensive buyer criteria
    Returns list of all matching buyers for a property
    """
    matches = []
    
    # Only get active, non-blacklisted buyers
    buyer_filters = BuyBoxFilter.objects.select_related(
        'buyer', 'land_type', 'access_type', 'preferred_utility'
    ).filter(
        is_active_buyer=True,
        is_blacklisted=False
    )

    for buyer_filter in buyer_filters:
        match_result = match_property_to_single_buyer(property_instance, buyer_filter)
        
        if match_result:
            matches.append({
                "buyer": {
                    "id": buyer_filter.buyer.id,
                    "name": buyer_filter.buyer.name,
                    "email": buyer_filter.buyer.email,
                    "asset_type": buyer_filter.get_asset_type_display(),
                    "land_type": buyer_filter.land_type.display_name if buyer_filter.land_type else None,
                    "buybox_filters": {
                        "lot_size_min": float(buyer_filter.lot_size_min) if buyer_filter.lot_size_min is not None else None,
                        "lot_size_max": float(buyer_filter.lot_size_max) if buyer_filter.lot_size_max is not None else None,
                        "zoning_preferences": buyer_filter.zoning,
                        "access_type": buyer_filter.access_type.display_name if buyer_filter.access_type else None,
                        "price_min": float(buyer_filter.price_min) if buyer_filter.price_min is not None else None,
                        "price_max": float(buyer_filter.price_max) if buyer_filter.price_max is not None else None,
                        "preferred_cities": buyer_filter.preferred_cities,
                        "preferred_counties": buyer_filter.preferred_counties,
                        "preferred_states": buyer_filter.preferred_states,
                        "preferred_zip_codes": buyer_filter.preferred_zip_codes,
                        "land_strategies": buyer_filter.land_strategies,
                        "land_property_types": buyer_filter.land_property_types,
                        "strict_requirements": buyer_filter.strict_requirements,
                    }
                },
                "match_score": match_result["match_score"],
                "likelihood": match_result["likelihood"],
                "factors_evaluated": match_result["factors_evaluated"],
                "factors_matched": match_result["factors_matched"],
                "match_details": match_result["match_details"]
            })

    # Sort by match score (highest first)
    return sorted(matches, key=lambda x: x["match_score"], reverse=True)


def check_strict_requirement(property_instance, requirement):
    """
    Check if a property meets a specific strict requirement
    Returns True if requirement is met, False otherwise
    """
    # You'll need to implement logic for each strict requirement based on your property model
    requirement_checks = {
        'legal_access_required': lambda prop: getattr(prop, 'has_legal_access', True),
        'utilities_at_road': lambda prop: 'utilities_at_road' in getattr(prop, 'property_characteristics', []),
        'no_flood_zone': lambda prop: 'flood_zone' not in getattr(prop, 'location_characteristics', []),
        'clear_title': lambda prop: getattr(prop, 'has_clear_title', True),
        'no_hoa': lambda prop: 'hoa_community' not in getattr(prop, 'location_characteristics', []),
        'paved_road_access': lambda prop: 'paved_road_access' in getattr(prop, 'property_characteristics', []),
        'mobile_home_allowed': lambda prop: getattr(prop, 'mobile_home_allowed', True),
    }
    
    check_function = requirement_checks.get(requirement)
    if check_function:
        return check_function(property_instance)
    
    # Default to True if requirement check is not implemented
    return True