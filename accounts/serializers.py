from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import UserProfile


class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    phone = serializers.CharField(write_only=True)  
    student_username = serializers.CharField(write_only=True, required=False, allow_blank=True)
    student_password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone',
            'student_username', 'student_password'
        )
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        phone = validated_data.pop('phone', None)
        student_username = validated_data.pop('student_username', None)
        student_password = validated_data.pop('student_password', None)

        user = User.objects.create_user(**validated_data)

        # fallback: if no student_password provided, use the actual signup password
        if not student_password:
            student_password = validated_data.get("password")

        return user, phone, student_username, student_password



class UserLoginSerializer(serializers.Serializer):
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
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password.')


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