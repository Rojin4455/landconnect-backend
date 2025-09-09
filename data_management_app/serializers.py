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

    latitude = serializers.DecimalField(max_digits=20, decimal_places=16, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=20, decimal_places=16, required=False, allow_null=True)
    place_id = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True) # Explicitly define place_id

    class Meta:
        model = PropertySubmission
        fields = [
            'id', 'llc_name', 'first_name', 'last_name', 'phone_number', 'email',
            'under_contract', 'agreed_price', 'parcel_id',
            'address', 'land_type', 'acreage', 'zoning',
            'lot_size', 'lot_size_unit',
            'exit_strategy', 'utilities', 'access_type',
            'description', 'extra_notes',
            'status', 'created_at', 'updated_at',
            'files', 'uploaded_files',
            'land_type_detail', 'utilities_detail',
            'access_type_detail', 'user_detail',
            'total_files_count', 'longitude', 'place_id', 'latitude'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at',
            'total_files_count'
        ]

    def get_land_type_detail(self, obj):
        if obj.land_type:
            return {
                'id': obj.land_type.id,
                'value': obj.land_type.value,
                'display_name': obj.land_type.display_name
            }
        return None

    def get_utilities_detail(self, obj):
        if obj.utilities:
            return {
                'id': obj.utilities.id,
                'value': obj.utilities.value,
                'display_name': obj.utilities.display_name
            }
        return None

    def get_access_type_detail(self, obj):
        if obj.access_type:
            return {
                'id': obj.access_type.id,
                'value': obj.access_type.value,
                'display_name': obj.access_type.display_name
            }
        return None

    def get_user_detail(self, obj):
        if obj.user:
            return {
                'id': obj.user.id,
                'username': obj.user.username,
                'first_name': obj.user.first_name,
                'last_name': obj.user.last_name,
                'email': obj.user.email
            }
        return None

    def validate_acreage(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Acreage must be greater than 0")
        return value

    def validate_agreed_price(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Agreed price must be greater than 0")
        return value
    
    def validate_phone_number(self, value):
        import re
        pattern = r'^\(\d{3}\)\s\d{3}-\d{4}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError("Phone number must be in format (XXX) XXX-XXXX")
        return value

    def validate(self, attrs):
        address = attrs.get('address', getattr(self.instance, 'address', None))
        parcel_id = attrs.get('parcel_id', getattr(self.instance, 'parcel_id', None))
    
        if not address and not parcel_id:
            raise serializers.ValidationError(
                "Either Sellers Property FULL Address or Parcel ID is required."
            )
        return attrs

    def validate(self, attrs):
        status = attrs.get("status", getattr(self.instance, "status", None))
        notes = attrs.get("buyer_rejected_notes", getattr(self.instance, "buyer_rejected_notes", None))

        if status == "buyer_rejected" and not notes:
            raise serializers.ValidationError({
                "buyer_rejected_notes": "This field is required when status is Buyer Rejected."
            })
        return attrs

    def create(self, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])

        # Create property submission
        # Ensure that fields like latitude, longitude, place_id are correctly popped by the serializer
        # and then passed to the create method.
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
            'llc_name', 'first_name', 'last_name', 'phone_number', 'email',
            'under_contract', 'agreed_price', 'parcel_id',
            'address', 'land_type', 'acreage', 'zoning',
            'lot_size', 'lot_size_unit',
            'exit_strategy', 'utilities', 'access_type',
            'description', 'extra_notes'
        ]



class PropertySubmissionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing properties"""
    land_type_name = serializers.CharField(source='land_type.display_name', read_only=True)
    utilities_name = serializers.CharField(source='utilities.display_name', read_only=True)
    access_type_name = serializers.CharField(source='access_type.display_name', read_only=True)
    
    class Meta:
        model = PropertySubmission
        fields = [
            'id', 'llc_name', 'first_name', 'last_name',
            'address', 'parcel_id', 'lot_size', 'lot_size_unit',
            'agreed_price', 'status', 'land_type_name',
            'utilities_name', 'access_type_name',
            'created_at', 'total_files_count'
        ]



class ConversationMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    property_submission_id = serializers.IntegerField(source='property_submission.id', read_only=True)

    class Meta:
        model = ConversationMessage
        fields = ['id', 'sender', 'sender_username', 'property_submission', 'property_submission_id', 'message', 'timestamp', 'is_admin', 'is_read']
        read_only_fields = ['sender', 'timestamp', 'is_admin', 'property_submission'] # sender, timestamp and is_admin are set by the view
        
        
class PropertyStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertySubmission
        fields = ['status', 'buyer_rejected_notes']

    def validate(self, attrs):
        if attrs.get("status") == "buyer_rejected" and not attrs.get("buyer_rejected_notes"):
            raise serializers.ValidationError(
                {"buyer_rejected_notes": "This field is required when rejecting a deal."}
            )
        return attrs