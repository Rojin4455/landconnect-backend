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
        "tags": ["JV_Partner"],
        "customFields": [
            {
                "id": "mTjrSQSWCFheYvanquKP",
                "value": student_username or user.username
            },
            {
                "id": "f5xfh7MXxAENmBYpD1BZ",
                "value": student_password   # actually the OTP
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

def update_contact_custom_fields_for_deal(email, first_name, last_name, llc_name, lot_address, deal_status):
    """
    Enhanced function with robust email handling and invalid email support
    """
    try:
        ghl_creds = GHLAuthCredentials.objects.first()
        if not ghl_creds:
            print("❌ No GHL credentials found in DB")
            return {"error": "No GHL credentials found"}

        headers = {
            "Authorization": f"Bearer {ghl_creds.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Version": "2021-07-28",
        }

        # Custom field IDs
        lot_address_field_id = "gGg0fM5MQm7r6S1Prctt"  # parentId: tx53zmVMWJy0e7TBe8It
        deal_status_field_id = "Z0sUyC214nxeDROj52ps"  # parentId: tx53zmVMWJy0e7TBe8It
        business_name_field_id = "CMVsvzugN5tf8dL2wLtc"  # no parentId - this is the problem

        print("===== DEBUG: Function Input =====")
        print(f"📧 Email: {email}")
        print(f"👤 First Name: {first_name}")
        print(f"👤 Last Name: {last_name}")
        print(f"🏢 LLC Name: {llc_name}")
        print(f"📍 Lot Address: {lot_address}")
        print(f"📌 Deal Status: {deal_status}")
        print(f"🔑 Location ID: {ghl_creds.location_id}")
        print("=================================")

        def find_contact_comprehensive():
            """
            Comprehensive contact search including invalid emails
            """
            contact_id = None
            
            # Method 1: Standard email search
            print("🔍 Method 1: Standard email search")
            try:
                search_url = f"{GHL_BASE_URL}/contacts"
                search_resp = requests.get(
                    search_url,
                    params={"email": email, "locationId": ghl_creds.location_id},
                    headers=headers,
                    timeout=10
                )
                
                print(f"🔎 Search Response [{search_resp.status_code}]: {search_resp.text[:500]}...")
                
                if search_resp.status_code == 200:
                    search_data = search_resp.json()
                    contacts = search_data.get("contacts") or []
                    if contacts:
                        contact_id = contacts[0]["id"]
                        print(f"✅ Found contact via standard search: {contact_id}")
                        return contact_id, "found_via_search"
                        
            except Exception as e:
                print(f"❌ Method 1 failed: {e}")
            
            # Method 2: Search by name (in case email search fails for invalid emails)
            if first_name and last_name:
                print("🔍 Method 2: Search by name")
                try:
                    search_resp = requests.get(
                        search_url,
                        params={
                            "query": f"{first_name} {last_name}",
                            "locationId": ghl_creds.location_id
                        },
                        headers=headers,
                        timeout=10
                    )
                    
                    if search_resp.status_code == 200:
                        search_data = search_resp.json()
                        contacts = search_data.get("contacts") or []
                        
                        # Look for contact with matching email (even if invalid)
                        for contact in contacts:
                            if contact.get("email", "").lower() == email.lower():
                                contact_id = contact["id"]
                                print(f"✅ Found contact via name search with matching email: {contact_id}")
                                return contact_id, "found_via_name_search"
                                
                except Exception as e:
                    print(f"❌ Method 2 failed: {e}")
            
            # Method 3: Try creation to detect duplicates
            print("🔍 Method 3: Creation attempt to detect duplicates")
            try:
                create_url = f"{GHL_BASE_URL}/contacts/"
                minimal_payload = {
                    "firstName": first_name or "Unknown",
                    "lastName": last_name or "Unknown", 
                    "email": email,
                    "locationId": ghl_creds.location_id
                }
                
                create_resp = requests.post(create_url, json=minimal_payload, headers=headers, timeout=10)
                print(f"📡 Creation attempt response [{create_resp.status_code}]: {create_resp.text[:500]}...")
                
                if create_resp.status_code == 201:
                    # Successfully created new contact
                    response_data = create_resp.json()
                    contact_id = response_data.get("contact", {}).get("id") or response_data.get("id")
                    print(f"✅ Created new contact: {contact_id}")
                    return contact_id, "newly_created"
                    
                elif create_resp.status_code in [400, 422]:
                    # Duplicate detected
                    error_data = create_resp.json()
                    duplicate_id = error_data.get("meta", {}).get("contactId")
                    if duplicate_id:
                        print(f"✅ Found existing contact via duplicate detection: {duplicate_id}")
                        return duplicate_id, "found_via_duplicate"
                        
            except Exception as e:
                print(f"❌ Method 3 failed: {e}")
            
            return None, "not_found"

        def update_contact_fields(contact_id, action_type):
            """
            Update contact with all custom fields
            """
            print(f"🔄 Updating contact {contact_id} (action: {action_type})")
            
            # Base contact info
            base_payload = {
                "firstName": first_name,
                "lastName": last_name,
                "email": email,
                "customFields": []
            }
            
            # Add company name if provided
            if llc_name:
                base_payload["companyName"] = llc_name
            
            # Add foldered custom fields
            if lot_address:
                base_payload["customFields"].append({
                    "id": lot_address_field_id,
                    "field_value": lot_address
                })
            
            if deal_status:
                base_payload["customFields"].append({
                    "id": deal_status_field_id,
                    "field_value": deal_status
                })
            
            # Add business name to custom fields as well (multiple strategies)
            if llc_name:
                base_payload["customFields"].append({
                    "id": business_name_field_id,
                    "field_value": llc_name
                })
            
            print(f"🛠 Update payload: {base_payload}")
            
            try:
                update_url = f"{GHL_BASE_URL}/contacts/{contact_id}"
                resp = requests.put(update_url, json=base_payload, headers=headers, timeout=10)
                
                print(f"📡 Update response [{resp.status_code}]: {resp.text[:300]}...")
                
                if resp.status_code in [200, 201]:
                    print("✅ Contact updated successfully")
                    return True
                else:
                    print(f"❌ Update failed with status {resp.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error during contact update: {e}")
                return False

        def try_additional_business_name_strategies(contact_id):
            """
            Try additional strategies for business name if the main update didn't work
            """
            if not llc_name:
                return True
                
            print(f"🔄 Trying additional business name strategies for contact {contact_id}")
            
            strategies = [
                # Strategy 1: Only business name in custom fields with 'value' key
                {
                    "name": "customFields with value key",
                    "payload": {
                        "customFields": [{
                            "id": business_name_field_id,
                            "value": llc_name
                        }]
                    }
                },
                
                # Strategy 2: PATCH request with custom fields
                {
                    "name": "PATCH customFields",
                    "payload": {
                        "customFields": [{
                            "id": business_name_field_id,
                            "field_value": llc_name
                        }]
                    },
                    "method": "PATCH"
                },
                
                # Strategy 3: Direct field assignment
                {
                    "name": "direct field assignment",
                    "payload": {business_name_field_id: llc_name}
                }
            ]
            
            update_url = f"{GHL_BASE_URL}/contacts/{contact_id}"
            
            for i, strategy in enumerate(strategies, 1):
                try:
                    print(f"🔄 Business name strategy {i}: {strategy['name']}")
                    
                    method = strategy.get('method', 'PUT')
                    if method == 'PUT':
                        resp = requests.put(update_url, json=strategy['payload'], headers=headers, timeout=10)
                    else:
                        resp = requests.patch(update_url, json=strategy['payload'], headers=headers, timeout=10)
                    
                    print(f"📡 Strategy {i} response [{resp.status_code}]: {resp.text[:200]}...")
                    
                    if resp.status_code in [200, 201]:
                        print(f"✅ Business name strategy {i} succeeded!")
                        return True
                        
                except Exception as e:
                    print(f"❌ Strategy {i} failed: {e}")
                    continue
            
            print("⚠️ All business name strategies attempted")
            return False

        def create_new_contact_with_validation_bypass():
            """
            Create new contact and try to bypass email validation issues
            """
            print("➕ Creating new contact with validation considerations...")
            
            # Strategy 1: Create with all fields at once
            base_payload = {
                "firstName": first_name,
                "lastName": last_name,
                "email": email,
                "locationId": ghl_creds.location_id,
                "customFields": []
            }
            
            # Add company name
            if llc_name:
                base_payload["companyName"] = llc_name
            
            # Add foldered custom fields
            if lot_address:
                base_payload["customFields"].append({
                    "id": lot_address_field_id,
                    "field_value": lot_address
                })
            
            if deal_status:
                base_payload["customFields"].append({
                    "id": deal_status_field_id,
                    "field_value": deal_status
                })
            
            # Add business name to custom fields
            if llc_name:
                base_payload["customFields"].append({
                    "id": business_name_field_id,
                    "field_value": llc_name
                })
            
            print(f"🛠 Creation payload: {base_payload}")
            
            try:
                create_url = f"{GHL_BASE_URL}/contacts/"
                resp = requests.post(create_url, json=base_payload, headers=headers, timeout=10)
                
                print(f"📡 Creation response [{resp.status_code}]: {resp.text[:300]}...")
                
                if resp.status_code == 201:
                    response_data = resp.json()
                    contact_id = response_data.get("contact", {}).get("id") or response_data.get("id")
                    if contact_id:
                        print(f"✅ Contact created successfully: {contact_id}")
                        print("ℹ️ Note: Email may be marked as invalid by GHL, but contact is created")
                        return contact_id
                
                return None
                    
            except Exception as e:
                print(f"❌ Error during contact creation: {e}")
                return None

        # Main execution flow
        print("🚀 Starting comprehensive contact processing...")
        
        # Step 1: Try to find existing contact
        contact_id, action_type = find_contact_comprehensive()
        
        if contact_id and action_type != "newly_created":
            # Contact exists, update it
            print(f"📝 Updating existing contact: {contact_id} (found via: {action_type})")
            
            update_success = update_contact_fields(contact_id, action_type)
            
            if update_success:
                # Try additional business name strategies if needed
                business_success = try_additional_business_name_strategies(contact_id)
                
                return {
                    "contact": {"id": contact_id}, 
                    "action": "updated",
                    "found_via": action_type,
                    "business_name_success": business_success,
                    "note": "Email may be marked as invalid by GHL due to mailbox validation"
                }
            else:
                return {"error": "Failed to update existing contact"}
        
        elif contact_id and action_type == "newly_created":
            # Contact was just created, try to add any missing fields
            print(f"📝 Newly created contact, ensuring all fields are set: {contact_id}")
            
            update_success = update_contact_fields(contact_id, "newly_created_update")
            business_success = try_additional_business_name_strategies(contact_id)
            
            return {
                "contact": {"id": contact_id}, 
                "action": "created",
                "business_name_success": business_success,
                "update_success": update_success,
                "note": "Email may be marked as invalid by GHL due to mailbox validation"
            }
        
        else:
            # No contact found, create new one
            print("➕ No existing contact found, creating new one...")
            
            contact_id = create_new_contact_with_validation_bypass()
            
            if contact_id:
                # Try additional business name strategies
                business_success = try_additional_business_name_strategies(contact_id)
                
                return {
                    "contact": {"id": contact_id}, 
                    "action": "created",
                    "business_name_success": business_success,
                    "note": "Email may be marked as invalid by GHL due to mailbox validation"
                }
            else:
                return {"error": "Failed to create new contact"}

    except requests.exceptions.RequestException as e:
        print(f"❌ Request Exception: {str(e)}")
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        print(f"❌ Unexpected Exception: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}

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
        # print("===== GHL Unread Message Update Debug =====")
        # print("Contact ID:", contact_id)
        # print("Unread Count to update:", unread_count)
        # print("API URL:", url)
        # print("Headers:", headers)
        # print("Payload:", payload)
        # print("===========================================")

        resp = requests.put(url, json=payload, headers=headers)

        # 🔹 Debug after request
        # print("===== GHL Response =====")
        # print("Status Code:", resp.status_code)
        # print("Response Text:", resp.text)
        # print("===========================================")

        resp.raise_for_status()
        return resp.json()

    except requests.exceptions.RequestException as e:
        # print("❌ Exception during GHL unread message update:", str(e))
        return {"error": str(e)}

def update_ghl_contact_otp(access_token, contact_id, otp):
    """Update OTP in GHL custom field (for login/signup)"""
    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28",
        "Accept": "application/json"
    }

    payload = {
        "customFields": [
            {
                "id": "f5xfh7MXxAENmBYpD1BZ",  # password/OTP field ID
                "value": otp
            }
        ]
    }

    try:
        response = requests.put(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            return True
        else:
            print("GHL OTP update failed:", response.text)
            return False
    except Exception as e:
        print("Exception while updating GHL OTP:", str(e))
        return False


def get_ghl_contact(access_token, contact_id):
    """Fetch GHL contact details by contactId"""
    url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get("contact", {})
        return None
    except Exception as e:
        print("Exception while fetching GHL contact:", str(e))
        return None


def check_contact_email_phone(access_token, contact_id, email, phone):
    """Check if a contact's email and phone match"""
    contact = get_ghl_contact(access_token, contact_id)
    if not contact:
        return False, "Contact not found"

    ghl_email = contact.get("email")
    ghl_phone = contact.get("phone")

    if ghl_email != email:
        return False, "Email does not match"
    if ghl_phone != phone:
        return False, "Phone does not match"

    return True, "Email and phone verified"