from .models import BuyBoxFilter
import re


def extract_location_components(address_or_components):
    """
    Enhanced location component extraction with better international support.
    Handles:
      1. Google Places API 'address_components' list
      2. Raw formatted address string (US and International formats)
    Always returns dict with keys: city, county, state, zip_code, full_address, country
    """
    components = {
        "city": None,
        "county": None,
        "state": None,
        "zip_code": None,
        "country": None,
        "full_address": None,
    }

    # Case 1: Google API address_components (list of dicts)
    if isinstance(address_or_components, list):
        for comp in address_or_components:
            types = comp.get("types", [])
            long_name = comp.get("long_name", "").strip()
            
            if "locality" in types or "sublocality" in types:  # City
                components["city"] = long_name
            elif "administrative_area_level_2" in types:  # County/District
                components["county"] = long_name
            elif "administrative_area_level_3" in types and not components["county"]:
                components["county"] = long_name
            elif "administrative_area_level_1" in types:  # State/Province
                components["state"] = long_name
            elif "country" in types:
                components["country"] = long_name
            elif "postal_code" in types:  # ZIP/Postal Code
                components["zip_code"] = long_name

        # Build full address
        components["full_address"] = ", ".join(
            [comp.get("long_name") for comp in address_or_components if comp.get("long_name")]
        ).strip()

        return components

    # Case 2: Plain string address - Enhanced for international addresses
    if isinstance(address_or_components, str):
        address = address_or_components.strip()
        components["full_address"] = address

        # Split by commas and clean up parts
        parts = [part.strip() for part in address.split(",") if part.strip()]
        
        if not parts:
            return components

        # Extract country (usually last part for international addresses)
        if len(parts) >= 1:
            potential_country = parts[-1].lower()
            # Common country identifiers
            known_countries = ['india', 'usa', 'united states', 'canada', 'uk', 'united kingdom', 
                             'australia', 'germany', 'france', 'japan', 'china']
            if any(country in potential_country for country in known_countries):
                components["country"] = parts[-1]
                parts = parts[:-1]  # Remove country from remaining parts

        # Extract ZIP/Postal code patterns
        for i, part in enumerate(parts):
            # US ZIP (5 or 9 digit)
            us_zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', part)
            # Indian PIN (6 digit)
            indian_pin_match = re.search(r'\b(\d{6})\b', part)
            # UK postcode pattern (simplified)
            uk_postcode_match = re.search(r'\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b', part.upper())
            
            if us_zip_match:
                components["zip_code"] = us_zip_match.group(1)
                # Remove ZIP from this part
                parts[i] = re.sub(r'\b\d{5}(?:-\d{4})?\b', '', part).strip()
            elif indian_pin_match:
                components["zip_code"] = indian_pin_match.group(1)
                parts[i] = re.sub(r'\b\d{6}\b', '', part).strip()
            elif uk_postcode_match:
                components["zip_code"] = uk_postcode_match.group(1)
                parts[i] = re.sub(r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b', '', part, flags=re.IGNORECASE).strip()

        # Clean up empty parts after ZIP extraction
        parts = [part for part in parts if part.strip()]

        # For common address patterns
        if len(parts) >= 1:
            # First non-empty part is usually the city/locality
            components["city"] = parts[0]
        
        if len(parts) >= 2:
            # Second part is often state/province or county
            components["state"] = parts[1]
            
        if len(parts) >= 3:
            # Third part might be county/district (common in Indian addresses)
            components["county"] = parts[2]

        # Clean up empty values
        for key in components:
            if components[key] and not components[key].strip():
                components[key] = None

    return components


def calculate_location_match_score(buyer_address, property_address):
    """
    Enhanced location match score with stricter matching and geographic awareness.
    Returns (score, debug_details) where score is between 0.0 and 1.0
    """
    if not buyer_address or not property_address:
        return 0.0, {"error": "missing address"}

    # Extract location components
    buyer_components = extract_location_components(buyer_address)
    property_components = extract_location_components(property_address)

    matches = 0
    total_components = 0
    debug_details = {
        "buyer_parsed": buyer_components,
        "property_parsed": property_components,
        "component_matches": {}
    }

    # Helper function for case-insensitive comparison
    def normalize_component(component):
        if not component:
            return None
        return component.strip().lower()

    # Country check - if different countries, return very low score
    buyer_country = normalize_component(buyer_components.get("country"))
    property_country = normalize_component(property_components.get("country"))
    
    if buyer_country and property_country and buyer_country != property_country:
        debug_details["country_mismatch"] = {
            "buyer": buyer_country,
            "property": property_country
        }
        return 0.1, debug_details  # Very low score for different countries

    # City match - Most important for local matching
    buyer_city = normalize_component(buyer_components.get("city"))
    property_city = normalize_component(property_components.get("city"))
    
    if buyer_city and property_city:
        total_components += 1
        if buyer_city == property_city:
            matches += 1
            debug_details["component_matches"]["city"] = True
        else:
            debug_details["component_matches"]["city"] = False

    # State/Province match
    buyer_state = normalize_component(buyer_components.get("state"))
    property_state = normalize_component(property_components.get("state"))
    
    if buyer_state and property_state:
        total_components += 1
        if buyer_state == property_state:
            matches += 1
            debug_details["component_matches"]["state"] = True
        else:
            debug_details["component_matches"]["state"] = False

    # County/District match
    buyer_county = normalize_component(buyer_components.get("county"))
    property_county = normalize_component(property_components.get("county"))
    
    if buyer_county and property_county:
        total_components += 1
        if buyer_county == property_county:
            matches += 1
            debug_details["component_matches"]["county"] = True
        else:
            debug_details["component_matches"]["county"] = False

    # ZIP/Postal code match
    buyer_zip = normalize_component(buyer_components.get("zip_code"))
    property_zip = normalize_component(property_components.get("zip_code"))
    
    if buyer_zip and property_zip:
        total_components += 1
        if buyer_zip == property_zip:
            matches += 1
            debug_details["component_matches"]["zip_code"] = True
        else:
            debug_details["component_matches"]["zip_code"] = False

    # Calculate score based on component matches
    if total_components > 0:
        score = matches / total_components
        debug_details["calculation"] = f"{matches}/{total_components} = {score:.2f}"
        return score, debug_details

    # Enhanced fallback logic - much stricter
    buyer_normalized = str(buyer_address).lower().strip()
    property_normalized = str(property_address).lower().strip()

    # Exact match
    if buyer_normalized == property_normalized:
        return 1.0, {"fallback": "exact_string_match"}
    
    # Check for meaningful overlap, not just any substring
    # Split into meaningful parts (not just any substring)
    buyer_parts = set(part.strip() for part in buyer_normalized.replace(',', ' ').split() if len(part.strip()) > 2)
    property_parts = set(part.strip() for part in property_normalized.replace(',', ' ').split() if len(part.strip()) > 2)
    
    if buyer_parts and property_parts:
        common_parts = buyer_parts.intersection(property_parts)
        total_unique_parts = buyer_parts.union(property_parts)
        
        if len(common_parts) > 0:
            overlap_ratio = len(common_parts) / len(total_unique_parts)
            # Only give partial credit if there's significant meaningful overlap
            if overlap_ratio >= 0.3:  # At least 30% meaningful overlap
                partial_score = min(0.7, overlap_ratio)  # Cap at 0.7 for partial matches
                debug_details["fallback"] = {
                    "type": "partial_word_overlap",
                    "common_words": list(common_parts),
                    "overlap_ratio": overlap_ratio,
                    "score": partial_score
                }
                return partial_score, debug_details

    # No meaningful match found
    debug_details["fallback"] = "no_meaningful_match"
    return 0.0, debug_details



def calculate_land_type_match_score(buyer_land_property_types, property_land_type):
    """
    Calculate land type match score
    buyer_land_property_types: list of land type choices from buyer (JSONField)
    property_land_type: LandType object or string value from property
    Returns 1.0 for match, 0.0 for no match
    """
    if not buyer_land_property_types or not property_land_type:
        return 0.0

    # Ensure buyer's land types is always a list
    if not isinstance(buyer_land_property_types, (list, tuple)):
        buyer_land_property_types = [buyer_land_property_types]

    # Extract the actual land type value from the property
    # If it's a ForeignKey object, get the appropriate field
    if hasattr(property_land_type, 'name'):  # Assuming LandType has a 'name' field
        property_type_value = property_land_type.name
    elif hasattr(property_land_type, 'display_name'):  # Or 'display_name' field
        property_type_value = property_land_type.display_name
    else:
        # If it's already a string value
        property_type_value = str(property_land_type)

    # Normalize for comparison
    property_type_normalized = property_type_value.lower().replace(" ", "_")
    
    # Check if any buyer land type matches
    for buyer_type in buyer_land_property_types:
        buyer_type_normalized = str(buyer_type).lower().replace(" ", "_")
        if buyer_type_normalized == property_type_normalized:
            return 1.0
    
    return 0.0


def calculate_exit_strategy_match_score(buyer_strategies, property_strategy):
    """
    Calculate exit strategy match score
    buyer_strategies: list (JSONField) OR single string
    property_strategy: single string
    Returns 1.0 for match, 0.0 for no match
    """
    if not buyer_strategies or not property_strategy:
        return 0.0

    # Normalize to lowercase strings for comparison
    if isinstance(buyer_strategies, str):
        buyer_strategies = [buyer_strategies]

    normalized_buyer = [str(s).strip().lower() for s in buyer_strategies]
    normalized_property = str(property_strategy).strip().lower()

    # Allow substring matching (e.g., "flip" matches "buy & flip")
    for strategy in normalized_buyer:
        if normalized_property in strategy or strategy in normalized_property:
            return 1.0

    return 0.0




def normalize_lot_size_to_acres(lot_size, unit):
    """
    Convert lot size to acres for consistent comparison
    """
    if not lot_size:
        return 0
    
    try:
        size = float(lot_size)
        if unit and unit.lower() == 'sqft':
            return size / 43560  # Convert sqft to acres
        elif unit and unit.lower() == 'acres':
            return size
        else:
            # Default assumption is acres if unit is not specified
            return size
    except (TypeError, ValueError):
        return 0

def calculate_lot_size_match_score(buyer_min_size, buyer_max_size, property_size, property_unit='acres'):
    """
    Calculate lot size match score
    Returns 1.0 if within range, 0.0 if outside range
    """
    if not property_size:
        return 0.0
    
    # Normalize property size to acres
    property_size_acres = normalize_lot_size_to_acres(property_size, property_unit)
    
    if property_size_acres == 0:
        return 0.0
    
    min_size = float(buyer_min_size) if buyer_min_size else 0
    max_size = float(buyer_max_size) if buyer_max_size else float('inf')
    
    if min_size <= property_size_acres <= max_size:
        return 1.0
    
    return 0.0

def calculate_price_match_score(buyer_min_price, buyer_max_price, property_price):
    """
    Calculate price match score
    Returns 1.0 if within range, 0.0 if outside range
    """
    if not property_price:
        return 0.0
    
    try:
        property_price = float(property_price)
    except (TypeError, ValueError):
        return 0.0
    
    min_price = float(buyer_min_price) if buyer_min_price else 0
    max_price = float(buyer_max_price) if buyer_max_price else float('inf')
    
    if min_price <= property_price <= max_price:
        return 1.0
    
    return 0.0

def match_property_to_single_buyer(property_instance, buyer_filter):
    """
    WEIGHTED SCORING ALGORITHM (Following Documentation Requirements)
    
    Weights according to documentation:
    - Location (City, County, Zip Code): 40%
    - Specific Type of Land: 30%
    - Exit Strategy: 20%
    - Lot Size: 5%
    - Agreed Price: 5%
    
    Total possible score: 100%
    """
    # Skip if buyer is inactive or blacklisted
    if not buyer_filter.is_active_buyer or buyer_filter.is_blacklisted:
        return None
    
    # Asset Type Check - Skip if buyer doesn't buy land
    if buyer_filter.asset_type == 'houses':
        return None  # This buyer only buys houses, skip for land properties
    
    # Initialize scoring components
    total_score = 0.0
    component_scores = {}
    component_contributions = {}
    match_details = {}
    
    # 1. LOCATION MATCH - 40% weight
    location_score, location_debug = calculate_location_match_score(
        buyer_filter.address,
        property_instance.address
    )
    
    location_contribution = location_score * 40.0  # Apply 40% weight
    total_score += location_contribution
    
    component_scores['location'] = location_score
    component_contributions['location'] = location_contribution
    match_details['location'] = (
        f"Location match: {location_score:.1%} (weighted: +{location_contribution:.1f}%) "
        f"→ {location_debug}"
    )

    # 2. LAND TYPE MATCH - 30% weight
    land_type_score = calculate_land_type_match_score(
        buyer_filter.land_property_types,    # ✅ JSON list from buyer
        property_instance.land_type          # ✅ LandType ForeignKey object from property
    )
    land_type_contribution = land_type_score * 30.0
    total_score += land_type_contribution
    
    component_scores['land_type'] = land_type_score
    component_contributions['land_type'] = land_type_contribution
    match_details['land_type'] = (
        f"Land type match: {land_type_score:.1%} (weighted: +{land_type_contribution:.1f}%)"
    )
    
    # 3. EXIT STRATEGY MATCH - 20% weight
    strategy_score = calculate_exit_strategy_match_score(
        buyer_filter.exit_strategy,
        property_instance.exit_strategy
    )
    strategy_contribution = strategy_score * 20.0
    total_score += strategy_contribution
    
    component_scores['exit_strategy'] = strategy_score
    component_contributions['exit_strategy'] = strategy_contribution
    match_details['exit_strategy'] = (
        f"Strategy match: {strategy_score:.1%} (weighted: +{strategy_contribution:.1f}%)"
    )
    
    # 4. LOT SIZE MATCH - 5% weight
    property_lot_size_acres = normalize_lot_size_to_acres(
        property_instance.lot_size, 
        getattr(property_instance, 'lot_size_unit', 'acres')
    )
    
    lot_size_score = calculate_lot_size_match_score(
        buyer_filter.lot_size_min,
        buyer_filter.lot_size_max,
        property_lot_size_acres,
        'acres'
    )
    lot_size_contribution = lot_size_score * 5.0
    total_score += lot_size_contribution
    
    component_scores['lot_size'] = lot_size_score
    component_contributions['lot_size'] = lot_size_contribution
    match_details['lot_size'] = (
        f"Size match: {lot_size_score:.1%} (weighted: +{lot_size_contribution:.1f}%) "
        f"[{property_lot_size_acres:.2f} acres]"
    )
    
    # 5. PRICE MATCH - 5% weight
    price_score = calculate_price_match_score(
        buyer_filter.price_min,
        buyer_filter.price_max,
        property_instance.agreed_price
    )
    price_contribution = price_score * 5.0
    total_score += price_contribution
    
    component_scores['price'] = price_score
    component_contributions['price'] = price_contribution
    match_details['price'] = (
        f"Price match: {price_score:.1%} (weighted: +{price_contribution:.1f}%) "
        f"[${property_instance.agreed_price:,}]"
    )
    
    # Determine fit category according to documentation
    if total_score > 45:
        likelihood = "Good Fit"
    elif total_score < 40:
        likelihood = "Poor Fit"
    else:
        likelihood = "Marginal Fit"
    
    # Only return matches with score >= 1%
    if total_score < 1:
        return None
    
    return {
        "match_score": round(total_score, 2),
        "likelihood": likelihood,
        "component_scores": {
            "location": round(component_scores['location'] * 100, 1),
            "land_type": round(component_scores['land_type'] * 100, 1),
            "exit_strategy": round(component_scores['exit_strategy'] * 100, 1),
            "lot_size": round(component_scores['lot_size'] * 100, 1),
            "price": round(component_scores['price'] * 100, 1),
        },
        "component_contributions": {
            "location": round(component_contributions['location'], 1),
            "land_type": round(component_contributions['land_type'], 1),
            "exit_strategy": round(component_contributions['exit_strategy'], 1),
            "lot_size": round(component_contributions['lot_size'], 1),
            "price": round(component_contributions['price'], 1),
        },
        "weighted_contribution": component_contributions,
        "match_details": match_details
    }


def match_property_to_buyers(property_instance):
    """
    Match property to all buyers and categorize results according to documentation
    """
    matches = []
    
    buyer_filters = BuyBoxFilter.objects.select_related(
        'buyer', 'access_type', 'preferred_utility'  # Add preferred_utility for efficiency
    ).filter(
        is_active_buyer=True,
        is_blacklisted=False,
        asset_type__in=['land', 'both']
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
                },
                "match_score": match_result["match_score"],
                "likelihood": match_result["likelihood"],
                "component_scores": match_result["component_scores"],
                "component_contributions": match_result["component_contributions"],
                "weighted_contribution": match_result["weighted_contribution"],
                "match_details": match_result["match_details"],
                "buyer_criteria": {
                    "location": buyer_filter.address,
                    "land_types": buyer_filter.land_property_types,
                    "strategies": buyer_filter.exit_strategy,
                    "lot_size_range": f"{buyer_filter.lot_size_min or 0}-{buyer_filter.lot_size_max or '∞'} acres",
                    "price_range": f"${buyer_filter.price_min or 0:,}-${buyer_filter.price_max or float('inf'):,}",
                }
            })

    matches.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Categorize matches according to documentation thresholds
    good_fit_buyers = [m for m in matches if m["match_score"] > 45]
    marginal_fit_buyers = [m for m in matches if 40 <= m["match_score"] <= 45]
    poor_fit_buyers = [m for m in matches if m["match_score"] < 40]
    
    return {
        "all_matches": matches,
        "good_fit_buyers": good_fit_buyers,
        "marginal_fit_buyers": marginal_fit_buyers,
        "poor_fit_buyers": poor_fit_buyers,
        "summary": {
            "total_buyers_evaluated": len(buyer_filters),
            "total_matches": len(matches),
            "good_fit_count": len(good_fit_buyers),
            "marginal_fit_count": len(marginal_fit_buyers),
            "poor_fit_count": len(poor_fit_buyers),
        }
    }
    
#GHL custom field update for link to buyer

import requests
import logging
from ghl_accounts.models import GHLAuthCredentials

logger = logging.getLogger(__name__)

CUSTOM_FIELD_ID = "A4ra922YgDx31mfbhEaJ"  # Your Buyer Deal URL custom field


def get_active_access_token():
    """
    Fetch the most recent stored access token from DB.
    (Later you can extend this to auto-refresh if expired).
    """
    creds = GHLAuthCredentials.objects.order_by("-id").first()
    if not creds:
        raise Exception("No GHL credentials found. Please authenticate first.")
    return creds.access_token


def update_buyer_deal_url(ghl_contact_id: str, deal_url: str):
    """
    Update the custom field (Buyer Deal URL) for a contact in GoHighLevel.

    :param ghl_contact_id: The GHL contact ID for the buyer
    :param deal_url: The URL of the deal page you want to save in GHL
    :return: API response JSON or None
    """
    try:
        access_token = get_active_access_token()
    except Exception as e:
        logger.error(f"Error fetching GHL access token: {e}")
        return None

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }

    payload = {
        "customFields": [
            {
                "id": CUSTOM_FIELD_ID,
                "field_value": deal_url
            }
        ]
    }

    try:
        response = requests.put(
            f"https://services.leadconnectorhq.com/contacts/{ghl_contact_id}",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating buyer deal URL in GHL: {e}")
        return None
