from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import UserProfile, UserGHLMapping
import random
from ghl_accounts.utils import check_contact_email_phone, get_ghl_contact
from ghl_accounts.models import GHLAuthCredentials

class UserSignupSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(write_only=True)  
    student_username = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name', 'phone',
            'student_username'
        )

    def validate(self, attrs):
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({"username": "Username already exists."})
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        if User.objects.filter(profile__phone=attrs['phone']).exists():
            raise serializers.ValidationError({"phone": "Phone already exists."})
        return attrs

    def create(self, validated_data):
        phone = validated_data.pop('phone', None)
        student_username = validated_data.pop('student_username', None)

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        print("OTP: ", otp)

        # Create user with OTP as password (temporary)
        user = User.objects.create_user(
            password=otp,
            **validated_data
        )

        return user, phone, student_username, otp



class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        phone = attrs.get('phone')
        errors = {}

        # Check if user exists in Django
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            errors['email'] = "Email not found."
            user = None

        # Check GHL credentials
        creds = GHLAuthCredentials.objects.last()
        if not creds:
            raise serializers.ValidationError({"detail": "No GHL credentials found."})

        if user:
            # ✅ Fetch ghl_contact_id from mapping
            try:
                mapping = UserGHLMapping.objects.get(user=user)
                contact_id = mapping.ghl_contact_id
            except UserGHLMapping.DoesNotExist:
                errors['detail'] = "GHL contactId not found for this user."
                contact_id = None

            if contact_id:
                is_valid, message = check_contact_email_phone(
                    creds.access_token,
                    contact_id,
                    email,
                    phone
                )
                if not is_valid:
                    errors['phone'] = message

        if errors:
            raise serializers.ValidationError(errors)

        attrs['user'] = user
        return attrs



class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid credentials.')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            if not (user.is_staff or user.is_superuser):
                raise serializers.ValidationError('Access denied. Admin privileges required.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password.')


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    email = serializers.EmailField(source="user.email", required=False)

    class Meta:
        model = UserProfile
        fields = ("id", "username", "first_name", "last_name", "email", "llc_name", "phone")

    def create(self, validated_data):
        user_data = validated_data.pop("user", {})
        user = self.context['request'].user  # use the logged-in user

        # Update user fields if provided
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        # Create the UserProfile
        profile = UserProfile.objects.create(user=user, **validated_data)
        return profile

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        user = instance.user

        # Update user fields
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        # Update profile fields
        return super().update(instance, validated_data)




class UserLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except Exception as e:
            raise serializers.ValidationError('Invalid token.')
        


# accounts/serializers.py (add these to your existing serializers file)
from rest_framework import serializers
from .models import LandType, Utility, AccessType


class LandTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandType
        fields = ['id', 'value', 'display_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_value(self, value):
        """Ensure value is lowercase and no spaces"""
        return value.lower().replace(' ', '_')


class UtilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Utility
        fields = ['id', 'value', 'display_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_value(self, value):
        """Ensure value is lowercase and no spaces"""
        return value.lower().replace(' ', '_')


class AccessTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessType
        fields = ['id', 'value', 'display_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_value(self, value):
        """Ensure value is lowercase and no spaces"""
        return value.lower().replace(' ', '_')