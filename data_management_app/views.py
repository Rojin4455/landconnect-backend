from rest_framework import generics, status, parsers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import PropertySubmission, PropertyFile, ConversationMessage
from .serializers import (
    PropertySubmissionSerializer, PropertySubmissionListSerializer,
    PropertySubmissionUpdateSerializer, PropertyFileSerializer,ConversationMessageSerializer, PropertyStatusUpdateSerializer
)
from django.contrib.auth.models import User
from decimal import Decimal
from buyer.utils import match_property_to_buyers
from django.db.models import Max, Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from ghl_accounts.utils import update_ghl_unread_message


class PropertySubmissionCreateView(generics.CreateAPIView):
    """Create a new property submission with file uploads"""
    queryset = PropertySubmission.objects.all()
    serializer_class = PropertySubmissionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def create(self, request, *args, **kwargs):
        # Create a mutable copy of request.data
        data = request.data.copy()

        print("Original data: ", data)

        # Convert frontend field names to backend field names and handle type conversion
        field_mapping = {
            'llcName': 'llc_name',
            'firstName': 'first_name',
            'lastName': 'last_name',
            'phoneNumber': 'phone_number',
            'email': 'email',
            'underContract': 'under_contract',
            'agreedPrice': 'agreed_price',
            'lotSize': 'lot_size',
            'lotSizeUnit': 'lot_size_unit',
            'exitStrategy': 'exit_strategy',
            'extraNotes': 'extra_notes',
            # existing ones you had
            'landType': 'land_type',
            'accessType': 'access_type',
            'place_id': 'place_id',
            'latitude': 'latitude',
            'longitude': 'longitude',
        }

        # Fields that need specific type conversion
        decimal_conversion_fields = ['latitude', 'longitude']
        string_conversion_fields = ['place_id'] # Add place_id here for explicit handling

        processed_data = {} # Use a new dictionary to store processed data

        for frontend_field, backend_field in field_mapping.items():
            if frontend_field in data:
                value = data.get(frontend_field) # Use .get() for safety

                if value is not None: # Only process if value exists
                    if backend_field in decimal_conversion_fields:
                        try:
                            processed_data[backend_field] = Decimal(str(value)) # Convert to string first for Decimal
                        except (ValueError, TypeError):
                            processed_data[backend_field] = None # Or handle as validation error
                    elif backend_field in string_conversion_fields:
                        processed_data[backend_field] = str(value) # Ensure it's a string
                    else:
                        # For other mapped fields, take the first value if it's a list (from QueryDict)
                        if isinstance(value, list) and len(value) == 1:
                            processed_data[backend_field] = value[0]
                        else:
                            processed_data[backend_field] = value
                else:
                    processed_data[backend_field] = None # Or appropriate default/null value

        # Copy over fields that were not explicitly mapped but should be included
        # This handles fields like 'address', 'acreage', 'zoning', 'topography', 'description', etc.
        # Ensure we don't overwrite already processed fields.
        for key, value in data.items():
            if key not in field_mapping and key not in processed_data: # Avoid re-processing mapped fields
                if isinstance(value, list) and len(value) == 1:
                    processed_data[key] = value[0]
                else:
                    processed_data[key] = value

        # Handle file uploads correctly
        uploaded_files = request.FILES.getlist('files')
        if uploaded_files:
            processed_data['uploaded_files'] = uploaded_files

        print("Processed data for serializer: ", processed_data)

        # Serialize and validate
        serializer = self.get_serializer(data=processed_data)
        serializer.is_valid(raise_exception=True)

        # Save with current user -> will trigger the create() method of serializer
        property_submission = serializer.save(user=request.user)

        return Response({
            'message': 'Property submission created successfully',
            'data': PropertySubmissionSerializer(
                property_submission,
                context={'request': request}
            ).data
        }, status=status.HTTP_201_CREATED)



class UserPropertySubmissionListView(generics.ListAPIView):
    """List property submissions for a specific user ID"""
    serializer_class = PropertySubmissionListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs.get('pk')
        user = get_object_or_404(User, pk=user_id)
        return PropertySubmission.objects.filter(user=user)
    

class PropertySubmissionListView(generics.ListAPIView):
    """List property submissions for the authenticated user along with unread message count"""
    serializer_class = PropertySubmissionListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = PropertySubmission.objects.filter(user=self.request.user)
        print(f"🔎 [DEBUG] get_queryset -> Found {qs.count()} property submissions for user {self.request.user}")
        return qs
    
    def list(self, request, *args, **kwargs):
        user = request.user
        print(f"\n🚀 [DEBUG] Entered PropertySubmissionListView.list() for user {user}")
        
        queryset = self.get_queryset()

        # Annotate unread counts
        queryset = queryset.annotate(
            unread_count=Count(
                'conversation_messages',
                filter=Q(conversation_messages__is_read=False) & ~Q(conversation_messages__sender=user)
            )
        )
        print(f"📦 [DEBUG] Annotated queryset with unread counts (total {queryset.count()} submissions)")

        data = []
        for prop in queryset:
            print(f"\n➡️ [DEBUG] Processing PropertySubmission ID={prop.id}, Address={prop.address}")

            last_message = prop.conversation_messages.order_by('-timestamp').first()
            if last_message:
                print(f"   💬 Last message: \"{last_message.message}\" at {last_message.timestamp}")
            else:
                print("   ⚠️ No messages found for this property")

            # Update GHL "Unread Message" custom field
            if hasattr(prop, "ghl_contact_id") and prop.ghl_contact_id:
                print(f"   🔄 Updating GHL unread message field for contact_id={prop.ghl_contact_id}, unread_count={prop.unread_count}")
                update_ghl_unread_message(prop.ghl_contact_id, prop.unread_count)
            else:
                print("   ⚠️ No GHL contact_id available, skipping update")

            data.append({
                "property_submission_id": prop.id,
                "address": prop.address,
                "last_message": last_message.message if last_message else None,
                "last_message_timestamp": last_message.timestamp if last_message else None,
                "unread_count": prop.unread_count,
            })

        print("\n✅ [DEBUG] Final response data prepared")
        return Response(data)



    

class AllPropertySubmissionListView(generics.ListAPIView):
    """List all property submissions (admins can filter by status)"""
    serializer_class = PropertySubmissionListSerializer
    permission_classes = [IsAuthenticated]
    queryset = PropertySubmission.objects.all()
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['status']   # filtering by status
    ordering_fields = ['created_at', 'updated_at']
    search_fields = ['address', 'parcel_id']


class PropertySubmissionDetailView(generics.RetrieveAPIView):
    """Get detailed view of a property submission"""
    serializer_class = PropertySubmissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PropertySubmission.objects.filter(user=self.request.user)
    

class PropertyDetailView(generics.RetrieveAPIView):
    """Get detailed view of a property submission"""
    serializer_class = PropertySubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PropertySubmission.objects.all()
    


class PropertyStatusUpdateView(generics.UpdateAPIView):
    """Admin view to update the status of a property submission"""
    serializer_class = PropertyStatusUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PropertySubmission.objects.all()



class PropertySubmissionUpdateView(generics.UpdateAPIView):
    """Update a property submission (excluding files)"""
    serializer_class = PropertySubmissionUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PropertySubmission.objects.filter(user=self.request.user)
    
    def update(self, request, *args, **kwargs):
        # Handle form data conversion
        data = request.data.copy()
        
        field_mapping = {
            'landType': 'land_type',
            'accessType': 'access_type',
        }
        
        for frontend_field, backend_field in field_mapping.items():
            if frontend_field in data:
                data[backend_field] = data.pop(frontend_field)
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        property_submission = serializer.save()
        
        return Response({
            'message': 'Property submission updated successfully',
            'data': PropertySubmissionSerializer(
                property_submission, 
                context={'request': request}
            ).data
        })


class PropertySubmissionDeleteView(generics.DestroyAPIView):
    """Delete a property submission"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PropertySubmission.objects.filter(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({
            'message': 'Property submission deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


class PropertyFileCreateView(generics.CreateAPIView):
    """Add files to an existing property submission"""
    serializer_class = PropertyFileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    
    def create(self, request, property_id, *args, **kwargs):
        property_submission = get_object_or_404(
            PropertySubmission, 
            id=property_id, 
            user=request.user
        )
        
        files = request.FILES.getlist('files')
        created_files = []
        
        for file in files:
            file_data = {
                'file': file,
                'property': property_submission.id,
                'original_name': file.name
            }
            serializer = self.get_serializer(data=file_data)
            serializer.is_valid(raise_exception=True)
            property_file = serializer.save(property=property_submission)
            created_files.append(property_file)
        
        return Response({
            'message': f'{len(created_files)} files uploaded successfully',
            'files': PropertyFileSerializer(
                created_files, 
                many=True, 
                context={'request': request}
            ).data
        }, status=status.HTTP_201_CREATED)


class PropertyFileDeleteView(generics.DestroyAPIView):
    """Delete a property file"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PropertyFile.objects.filter(property__user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({
            'message': 'File deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


# Admin views for managing property submissions
class AdminPropertySubmissionListView(generics.ListAPIView):
    serializer_class = PropertySubmissionListSerializer
    permission_classes = [IsAuthenticated]  # or IsAdminUser if only admins
    
    queryset = PropertySubmission.objects.all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'updated_at']
    search_fields = ['address', 'parcel_id', 'llc_name', 'first_name', 'last_name']



class ConversationMessageListView(generics.ListAPIView):
    """
    API endpoint to list all messages for a specific property submission.
    Admins can view messages for any property.
    Users can only view messages for their own properties.
    """
    serializer_class = ConversationMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        property_submission_id = self.kwargs['property_submission_id']
        property_submission = get_object_or_404(PropertySubmission, id=property_submission_id)

        # Check object-level permission using has_object_permission
        self.check_object_permissions(self.request, property_submission)

        return ConversationMessage.objects.filter(property_submission=property_submission)


class ConversationMessageCreateView(generics.CreateAPIView):
    """
    API endpoint to send a new message for a specific property submission.
    The sender is automatically set to the authenticated user.
    is_admin is set based on whether the sending user is an admin.
    Users can only send messages for their own properties.
    Admins can send messages for any property.
    """
    serializer_class = ConversationMessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        property_submission_id = self.kwargs['property_submission_id']
        property_submission = get_object_or_404(PropertySubmission, id=property_submission_id)

        # Check object-level permission using has_object_permission
        self.check_object_permissions(self.request, property_submission)

        is_admin_message = self.request.user.is_staff
        serializer.save(
            sender=self.request.user,
            property_submission=property_submission,
            is_admin=is_admin_message
        )
        

class ConversationInboxView(generics.ListAPIView):
    """
    Returns a list of conversations (one per property submission)
    with last message + unread count.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        user = request.user
        qs = PropertySubmission.objects.all()

        if not user.is_staff:  # normal users see only their own
            qs = qs.filter(user=user)

        data = []
        for prop in qs:
            last_message = prop.conversation_messages.order_by('-timestamp').first()
            unread_count = prop.conversation_messages.filter(
                is_read=False
            ).exclude(sender=user).count()

            if last_message:
                data.append({
                    "property_submission_id": prop.id,
                    "property_title": getattr(prop, "address", f"Property {prop.id}"),
                    "partner_name": prop.user.username,
                    "last_message": {
                        "id": last_message.id,
                        "sender": {
                            "id": last_message.sender.id,
                            "name": last_message.sender.username
                        },
                        "content": last_message.message,
                        "timestamp": last_message.timestamp,
                    },
                    "unread_count": unread_count,
                })

        return Response(data)


class ConversationMarkReadView(generics.UpdateAPIView):
    """
    Marks all messages in a property conversation as read for the current user.
    """
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        property_submission_id = self.kwargs['property_submission_id']
        property_submission = get_object_or_404(PropertySubmission, id=property_submission_id)

        # Mark as read all messages NOT sent by this user
        ConversationMessage.objects.filter(
            property_submission=property_submission,
            is_read=False
        ).exclude(sender=request.user).update(is_read=True)

        return Response({"status": "messages marked as read"})

        
class PropertyMatchingBuyersView(generics.RetrieveAPIView):
    """
    Get all matching buyers for a specific property with weighted scoring.
    This endpoint is for admin use to view buyer matches in the deals details page.
    """
    permission_classes = [IsAuthenticated]  
    
    def get(self, request, property_id):
        """
        GET /api/properties/{property_id}/matching-buyers/
        
        Returns:
        {
            "property_details": {
                "id": 1,
                "address": "123 Main St, Tampa, FL 33602",
                "agreed_price": 50000,
                "lot_size": 2.5,
                "lot_size_unit": "acres",
                "land_type": "Residential Vacant",
                "exit_strategy": "infill"
            },
            "matching_results": {
                "summary": {
                    "total_buyers_evaluated": 25,
                    "total_matches": 15,
                    "good_fit_count": 8,
                    "marginal_fit_count": 3,
                    "poor_fit_count": 4
                },
                "good_fit_buyers": [...],
                "marginal_fit_buyers": [...],
                "poor_fit_buyers": [...],
                "all_matches": [...]
            }
        }
        """
        try:
            # Get the property instance
            property_instance = get_object_or_404(PropertySubmission, id=property_id)
            
            # Use your existing matching function
            matching_results = match_property_to_buyers(property_instance)
            
            # Prepare property details for response
            property_details = {
                "id": property_instance.id,
                "address": property_instance.address,
                "agreed_price": float(property_instance.agreed_price) if property_instance.agreed_price else None,
                "lot_size": float(property_instance.lot_size) if property_instance.lot_size else None,
                "lot_size_unit": property_instance.lot_size_unit,
                "land_type": property_instance.land_type.display_name if property_instance.land_type else None,
                "exit_strategy": property_instance.get_exit_strategy_display() if property_instance.exit_strategy else None,
                "exit_strategy_value": property_instance.exit_strategy,
                "created_at": property_instance.created_at,
                "status": property_instance.get_status_display(),
                "acreage": float(property_instance.acreage) if property_instance.acreage else None,
            }
            
            return Response({
                "success": True,
                "property_details": property_details,
                "matching_results": matching_results
            }, status=status.HTTP_200_OK)
            
        except PropertySubmission.DoesNotExist:
            return Response({
                "success": False,
                "error": "Property not found",
                "message": f"No property found with ID {property_id}"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": "Internal server error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PropertyMatchingBuyerDetailView(generics.RetrieveAPIView):
    """
    Get detailed matching information for a specific buyer-property pair.
    Useful for debugging or detailed analysis of why a specific match score was calculated.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, property_id, buyer_id):
        """
        GET /api/properties/{property_id}/matching-buyers/{buyer_id}/
        
        Returns detailed breakdown of match calculation for a specific buyer.
        """
        try:
            from buyer.models import BuyBoxFilter  # Adjust import path as needed
            from buyer.utils import match_property_to_single_buyer
            
            # Get the property and buyer instances
            property_instance = get_object_or_404(PropertySubmission, id=property_id)
            buyer_filter = get_object_or_404(BuyBoxFilter, buyer__id=buyer_id)
            
            # Calculate match for this specific buyer
            match_result = match_property_to_single_buyer(property_instance, buyer_filter)
            
            if not match_result:
                return Response({
                    "success": False,
                    "error": "No match found",
                    "message": "This buyer doesn't match this property or buyer is inactive/blacklisted"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Prepare detailed response
            response_data = {
                "success": True,
                "property_details": {
                    "id": property_instance.id,
                    "address": property_instance.address,
                    "agreed_price": float(property_instance.agreed_price) if property_instance.agreed_price else None,
                    "lot_size": float(property_instance.lot_size) if property_instance.lot_size else None,
                    "lot_size_unit": property_instance.lot_size_unit,
                    "land_type": property_instance.land_type.display_name if property_instance.land_type else None,
                    "exit_strategy": property_instance.get_exit_strategy_display(),
                },
                "buyer_details": {
                    "id": buyer_filter.buyer.id,
                    "name": buyer_filter.buyer.name,
                    "email": buyer_filter.buyer.email,
                    "asset_type": buyer_filter.get_asset_type_display(),
                    "is_active": buyer_filter.is_active_buyer,
                    "is_blacklisted": buyer_filter.is_blacklisted,
                },
                "match_analysis": match_result,
                "criteria_comparison": {
                    "location": {
                        "property": property_instance.address,
                        "buyer_wants": buyer_filter.address,
                    },
                    "land_type": {
                        "property": property_instance.land_type.display_name if property_instance.land_type else None,
                        "buyer_wants": buyer_filter.land_property_types,  # ✅ Fixed: Use land_property_types JSONField
                    },
                    "exit_strategy": {
                        "property": property_instance.exit_strategy,
                        "buyer_wants": buyer_filter.exit_strategy,  # ✅ Fixed: Use exit_strategy instead of land_strategies
                    },
                    "lot_size": {
                        "property": f"{property_instance.lot_size} {property_instance.lot_size_unit}",
                        "buyer_wants": f"{buyer_filter.lot_size_min or 0}-{buyer_filter.lot_size_max or '∞'} acres",
                    },
                    "price": {
                        "property": float(property_instance.agreed_price) if property_instance.agreed_price else None,
                        "buyer_wants": f"${buyer_filter.price_min or 0:,}-${buyer_filter.price_max or float('inf'):,}",
                    }
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except PropertySubmission.DoesNotExist:
            return Response({
                "success": False,
                "error": "Property not found"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except BuyBoxFilter.DoesNotExist:
            return Response({
                "success": False,
                "error": "Buyer not found"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": "Internal server error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)