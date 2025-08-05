def match_property_to_buyers(property_instance):
    from .models import BuyBoxFilter
    matches = []
    
    buyer_filters = BuyBoxFilter.objects.select_related('buyer', 'land_type', 'access_type').all()

    for buyer_filter in buyer_filters:
        score = 0
        total = 5  # total factors considered

        if buyer_filter.land_type and buyer_filter.land_type == property_instance.land_type:
            score += 1
        if buyer_filter.lot_size_min is not None and buyer_filter.lot_size_max is not None:
            if buyer_filter.lot_size_min <= property_instance.acreage <= buyer_filter.lot_size_max:
                score += 1
        if buyer_filter.zoning and property_instance.zoning:
            if buyer_filter.zoning.lower() in property_instance.zoning.lower():
                score += 1
        if buyer_filter.access_type and buyer_filter.access_type == property_instance.access_type:
            score += 1
        if buyer_filter.price_min is not None and buyer_filter.price_max is not None:
            if buyer_filter.price_min <= property_instance.asking_price <= buyer_filter.price_max:
                score += 1

        percentage = (score / total) * 100
        if percentage >= 70:
            likelihood = "High"
        elif percentage >= 40:
            likelihood = "Medium"
        else:
            likelihood = "Low"

        matches.append({
            "buyer": {
                "id": buyer_filter.buyer.id,
                "asset_type": buyer_filter.land_type.display_name if buyer_filter.land_type else None,
                "buybox_filters": {
                    "lot_size_min": float(buyer_filter.lot_size_min) if buyer_filter.lot_size_min is not None else None,
                    "lot_size_max": float(buyer_filter.lot_size_max) if buyer_filter.lot_size_max is not None else None,
                    "zoning": buyer_filter.zoning,
                    "access_type": buyer_filter.access_type.display_name if buyer_filter.access_type else None,
                    "price_min": float(buyer_filter.price_min) if buyer_filter.price_min is not None else None,
                    "price_max": float(buyer_filter.price_max) if buyer_filter.price_max is not None else None
                }
            },
            "match_score": round(percentage, 2),
            "likelihood": likelihood
        })

    return sorted(matches, key=lambda x: x["match_score"], reverse=True)


