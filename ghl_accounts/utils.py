import requests

def create_ghl_contact_for_buyer(access_token, location_id, buyer):
    """Create a GHL contact for Buyer"""
    url = "https://services.leadconnectorhq.com/contacts/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28",
        "Accept": "application/json"
    }
    payload = {
        "locationId": location_id,
        "name": buyer.name,
        "email": buyer.email,
        "phone": buyer.phone,
        "tags": ["Buyer"]
    }

    print("=== GHL Buyer Contact Creation Debug ===")
    print("Payload:", payload)

    try:
        response = requests.post(url, headers=headers, json=payload)
        print("Status Code:", response.status_code)
        print("Response Text:", response.text)

        if response.status_code in [200, 201]:
            data = response.json()
            return data.get("contact", {}).get("id")
        return None
    except Exception as e:
        print("Exception in buyer GHL contact:", str(e))
        return None


def create_ghl_contact_for_user(access_token, location_id, user, phone):
    """Create a GHL contact for User"""
    url = "https://services.leadconnectorhq.com/contacts/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28",
        "Accept": "application/json"
    }
    full_name = f"{user.first_name} {user.last_name}".strip() or user.username
    payload = {
        "locationId": location_id,
        "name": full_name,
        "email": user.email,
        "phone": phone,
        "tags": ["User"]
    }

    print("=== GHL User Contact Creation Debug ===")
    print("Payload:", payload)

    try:
        response = requests.post(url, headers=headers, json=payload)
        print("Status Code:", response.status_code)
        print("Response Text:", response.text)

        if response.status_code in [200, 201]:
            data = response.json()
            return data.get("contact", {}).get("id")
        return None
    except Exception as e:
        print("Exception in user GHL contact:", str(e))
        return None
