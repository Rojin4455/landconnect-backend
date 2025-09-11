import requests
from ghl_accounts.models import GHLAuthCredentials

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


def create_ghl_contact_for_user(access_token, location_id, user, phone, student_username=None, student_password=None):
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
        "tags": ["User"],
        "customFields": [
            {
                "id": "mTjrSQSWCFheYvanquKP",
                "value": student_username or user.username
            },
            {
                "id": "f5xfh7MXxAENmBYpD1BZ",
                "value": student_password   # now guaranteed not None
            }
        ]

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


GHL_BASE_URL = "https://services.leadconnectorhq.com"

def update_contact_custom_fields_for_deal(email, first_name, last_name, lot_address, deal_status):
    """
    Create a new GHL contact with minimal required info + custom fields inside 'Deal Submission' folder.
    Only creates custom fields inside the folder, no other top-level fields.
    """
    try:
        ghl_creds = GHLAuthCredentials.objects.first()
        if not ghl_creds:
            print(" No GHL credentials found")
            return {"error": "No GHL credentials found"}

        headers = {
            "Authorization": f"Bearer {ghl_creds.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Version": "2021-07-28"
        }

        # Folder ID for 'Deal Submission'
        deal_folder_id = "tx53zmVMWJy0e7TBe8It"

        payload = {
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "locationId": ghl_creds.location_id,
            "customFields": [
                {
                    "id": "gGg0fM5MQm7r6S1Prctt",  # Lot Address
                    "field_value": lot_address or "",
                    "parentId": deal_folder_id
                },
                {
                    "id": "Z0sUyC214nxeDROj52ps",  # Deal Status
                    "field_value": deal_status or "",
                    "parentId": deal_folder_id
                }
            ]
        }

        print("Creating GHL contact with foldered custom fields")
        print("Payload:", payload)

        url = f"{GHL_BASE_URL}/contacts/"
        resp = requests.post(url, json=payload, headers=headers)

        print("Status Code:", resp.status_code)
        print("Response Text:", resp.text)

        resp.raise_for_status()
        return resp.json()

    except requests.exceptions.RequestException as e:
        print("Exception during GHL contact creation:", str(e))
        return {"error": str(e)}


def update_ghl_deal_status(contact_id, deal_status):
    """
    Update the 'Deal Status' custom field for a given GHL contact.
    """
    try:
        ghl_creds = GHLAuthCredentials.objects.first()
        if not ghl_creds:
            return {"error": "No GHL credentials found"}

        headers = {
            "Authorization": f"Bearer {ghl_creds.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Version": "2021-07-28"
        }

        # Deal Status field inside 'Deal Submission' folder
        deal_status_field_id = "Z0sUyC214nxeDROj52ps"

        payload = {
            "customFields": [
                {
                    "id": deal_status_field_id,
                    "field_value": deal_status
                }
            ]
        }

        url = f"{GHL_BASE_URL}/contacts/{contact_id}"
        resp = requests.put(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def update_ghl_unread_message(contact_id, unread_count):
    """
    Update only the 'Unread Message' custom field inside 'Deal Submission' folder for a given GHL contact.
    Includes detailed debug prints.
    """
    try:
        ghl_creds = GHLAuthCredentials.objects.first()
        if not ghl_creds:
            print("❌ No GHL credentials found")
            return {"error": "No GHL credentials found"}

        headers = {
            "Authorization": f"Bearer {ghl_creds.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Version": "2021-07-28"
        }

        # Custom Field ID for 'Unread Message'
        unread_message_field_id = "YXLt2BcbMSjRbaHOACld"

        payload = {
            "customFields": [
                {
                    "id": unread_message_field_id,
                    "field_value": str(unread_count),  # GHL expects text values
                    "parentId": "tx53zmVMWJy0e7TBe8It"  # Deal Submission folder
                }
            ]
        }

        url = f"{GHL_BASE_URL}/contacts/{contact_id}"

        # 🔹 Debug before request
        print("===== GHL Unread Message Update Debug =====")
        print("Contact ID:", contact_id)
        print("Unread Count to update:", unread_count)
        print("API URL:", url)
        print("Headers:", headers)
        print("Payload:", payload)
        print("===========================================")

        resp = requests.put(url, json=payload, headers=headers)

        # 🔹 Debug after request
        print("===== GHL Response =====")
        print("Status Code:", resp.status_code)
        print("Response Text:", resp.text)
        print("===========================================")

        resp.raise_for_status()
        return resp.json()

    except requests.exceptions.RequestException as e:
        print("❌ Exception during GHL unread message update:", str(e))
        return {"error": str(e)}
