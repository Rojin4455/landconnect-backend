from rest_framework import serializers
from django.contrib.auth.models import User
from .models import PropertySubmission, PropertyFile, LandType, Utility, AccessType,ConversationMessage


class PropertyFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyFile
        fields = [
            'id', 'file', 'file_url', 'file_type', 'original_name', 
            'file_size', 'description', 'created_at'
        ]
        read_only_fields = ['id', 'file_type', 'file_size', 'created_at']
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class PropertySubmissionSerializer(serializers.ModelSerializer):
    files = PropertyFileSerializer(many=True, read_only=True)
    uploaded_files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )
    
    # Display related object details
    land_type_detail = serializers.SerializerMethodField()
    utilities_detail = serializers.SerializerMethodField()
    access_type_detail = serializers.SerializerMethodField()
    user_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertySubmission
        fields = [
            'id', 'address', 'land_type', 'acreage', 'zoning', 'asking_price',
            'estimated_aev', 'development_costs', 'utilities', 'access_type',
            'topography', 'environmental_factors', 'nearest_attraction',
            'description', 'status', 'created_at', 'updated_at',
            'files', 'uploaded_files', 'land_type_detail', 'utilities_detail',
            'access_type_detail', 'user_detail', 'total_files_count'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'created_at', 'updated_at', 
            'total_files_count'
        ]
    
    def get_land_type_detail(self, obj):
        return {
            'id': obj.land_type.id,
            'value': obj.land_type.value,
            'display_name': obj.land_type.display_name
        }
    
    def get_utilities_detail(self, obj):
        return {
            'id': obj.utilities.id,
            'value': obj.utilities.value,
            'display_name': obj.utilities.display_name
        }
    
    def get_access_type_detail(self, obj):
        return {
            'id': obj.access_type.id,
            'value': obj.access_type.value,
            'display_name': obj.access_type.display_name
        }
    
    def get_user_detail(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'email': obj.user.email
        }
    
    def validate_acreage(self, value):
        if value <= 0:
            raise serializers.ValidationError("Acreage must be greater than 0")
        return value
    
    def validate_asking_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Asking price must be greater than 0")
        return value
    
    def create(self, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])
        
        # Create property submission
        property_submission = PropertySubmission.objects.create(**validated_data)
        
        # Handle file uploads
        for file in uploaded_files:
            PropertyFile.objects.create(
                property=property_submission,
                file=file,
                original_name=file.name
            )
        
        return property_submission


class PropertySubmissionUpdateSerializer(serializers.ModelSerializer):
    """Separate serializer for updates (without file upload)"""
    class Meta:
        model = PropertySubmission
        fields = [
            'address', 'land_type', 'acreage', 'zoning', 'asking_price',
            'estimated_aev', 'development_costs', 'utilities', 'access_type',
            'topography', 'environmental_factors', 'nearest_attraction',
            'description'
        ]



class PropertySubmissionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing properties"""
    land_type_name = serializers.CharField(source='land_type.display_name', read_only=True)
    utilities_name = serializers.CharField(source='utilities.display_name', read_only=True)
    access_type_name = serializers.CharField(source='access_type.display_name', read_only=True)
    
    class Meta:
        model = PropertySubmission
        fields = [
            'id', 'address', 'acreage', 'asking_price', 'status',
            'land_type_name', 'utilities_name', 'access_type_name',
            'created_at', 'total_files_count'
        ]



class ConversationMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    property_submission_id = serializers.IntegerField(source='property_submission.id', read_only=True)

    class Meta:
        model = ConversationMessage
        fields = ['id', 'sender', 'sender_username', 'property_submission', 'property_submission_id', 'message', 'timestamp', 'is_admin']
        read_only_fields = ['sender', 'timestamp', 'is_admin', 'property_submission'] # sender, timestamp and is_admin are set by the view