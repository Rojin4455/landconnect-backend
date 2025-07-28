from rest_framework import generics, status, parsers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import PropertySubmission, PropertyFile, ConversationMessage
from .serializers import (
    PropertySubmissionSerializer, PropertySubmissionListSerializer,
    PropertySubmissionUpdateSerializer, PropertyFileSerializer,ConversationMessageSerializer
)
from django.contrib.auth.models import User
from decimal import Decimal



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
            'landType': 'land_type',
            'askingPrice': 'asking_price',
            'estimatedAEV': 'estimated_aev',
            'developmentCosts': 'development_costs',
            'accessType': 'access_type',
            'environmentalFactors': 'environmental_factors',
            'nearestAttraction': 'nearest_attraction',
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
        serializer = self.get_serializer(data=processed_data) # Pass the processed_data
        serializer.is_valid(raise_exception=True)

        # Save with current user
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
    """List property submissions for the authenticated user"""
    serializer_class = PropertySubmissionListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PropertySubmission.objects.filter(user=self.request.user)
    
    
class AllPropertySubmissionListView(generics.ListAPIView):
    """List property submissions for the authenticated user"""
    serializer_class = PropertySubmissionListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PropertySubmission.objects.all()

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
    serializer_class = PropertySubmissionSerializer
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
            'askingPrice': 'asking_price',
            'estimatedAEV': 'estimated_aev',
            'developmentCosts': 'development_costs',
            'accessType': 'access_type',
            'environmentalFactors': 'environmental_factors',
            'nearestAttraction': 'nearest_attraction',
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
    """Admin view to list all property submissions"""
    queryset = PropertySubmission.objects.all()
    serializer_class = PropertySubmissionListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Only allow staff/superuser access
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return PropertySubmission.objects.none()
        
        queryset = PropertySubmission.objects.all()
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    



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