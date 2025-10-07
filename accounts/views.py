from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny,IsAuthenticatedOrReadOnly,IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from .serializers import (
    UserSignupSerializer,
    UserLoginSerializer,
    AdminLoginSerializer,
    UserProfileSerializer,
    UserLogoutSerializer
)
from django.shortcuts import get_object_or_404
from .models import LandType, Utility, AccessType, UserProfile, UserGHLMapping
from .serializers import LandTypeSerializer, UtilitySerializer, AccessTypeSerializer
from ghl_accounts.utils import create_ghl_contact_for_user, update_ghl_contact_otp, normalize_phone
from ghl_accounts.models import GHLAuthCredentials
from rest_framework.exceptions import ValidationError
from data_management_app.models import PropertySubmission
from rest_framework.views import APIView
import random
from datetime import timedelta


def get_tokens_for_user(user, lifetime_hours=48):
    """Generate JWT tokens for user with custom access token lifetime"""
    refresh = RefreshToken.for_user(user)

    # Set custom lifetime for access token
    access = refresh.access_token
    access.set_exp(lifetime=timedelta(hours=lifetime_hours))

    return {
        'refresh': str(refresh),
        'access': str(access),
    }


class UserSignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSignupSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user, phone, student_username, otp = serializer.save()

        creds = GHLAuthCredentials.objects.last()
        ghl_contact_id = None
        if creds:
            ghl_contact_id = create_ghl_contact_for_user(
                creds.access_token,
                creds.location_id,
                user,
                phone=phone,
                student_username=student_username,
                student_password=otp,  # store OTP as custom field
            )
            print("GHL contact created:", ghl_contact_id)

            # ✅ Store mapping in DB
            if ghl_contact_id:
                UserGHLMapping.objects.create(user=user, ghl_contact_id=ghl_contact_id, phone=phone)

        return Response({
            "message": "Signup successful. OTP has been sent to your contact details.",
            "user_id": user.id,
            "username": user.username
        }, status=status.HTTP_201_CREATED)


class OTPVerifyView(APIView):
    """Step 2: Verify OTP and activate account"""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        otp = request.data.get("otp")

        if not username or not otp:
            return Response({"error": "Username and OTP are required."}, status=400)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "Invalid username"}, status=400)

        if not user.check_password(otp):
            return Response({"error": "Invalid OTP"}, status=400)

        # ✅ OTP matched → activate account
        user.is_active = True
        user.save()

        tokens = get_tokens_for_user(user)

        return Response({
            "message": "OTP verified successfully. Signup completed.",
            "tokens": tokens
        }, status=200)

class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        print("Login OTP:", otp)

        # Temporarily set OTP as password
        user.set_password(otp)
        user.save()

        # Update OTP in GHL custom field
        creds = GHLAuthCredentials.objects.last()
        mapping = UserGHLMapping.objects.get(user=user)
        contact_id = mapping.ghl_contact_id
        update_ghl_contact_otp(creds.access_token, contact_id, otp)

        return Response({
            "message": "OTP generated and sent to your phone.",
            "user_id": user.id,
            "username": user.username
        }, status=200)


class UserLoginOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = normalize_phone(request.data.get("phone"))
        otp = request.data.get("otp")

        if not phone or not otp:
            return Response({"error": "Phone and OTP are required."}, status=400)

        # ✅ Find user via UserGHLMapping
        try:
            mapping = UserGHLMapping.objects.get(phone=phone)
            user = mapping.user
        except UserGHLMapping.DoesNotExist:
            return Response({"error": "Invalid Phone"}, status=400)

        # Verify OTP
        if not user.check_password(otp):
            return Response({"error": "Invalid OTP"}, status=400)

        # Issue JWT valid for 48 hours
        tokens = get_tokens_for_user(user, lifetime_hours=48)

        return Response({
            "message": "Login successful.",
            "tokens": tokens
        }, status=200)
        
        
class AdminLoginView(generics.GenericAPIView):
    """Admin login endpoint"""
    serializer_class = AdminLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        tokens = get_tokens_for_user(user)
        
        return Response({
            'message': 'Admin login successful',
            'admin': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            },
            'tokens': tokens
        }, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView, generics.CreateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Return the user's profile if it exists."""
        try:
            return self.request.user.profile
        except UserProfile.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        profile = self.get_object()

        if not profile:
            # Return user details only (pre-filled data)
            user = request.user
            data = {
                "id": None,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "llc_name": None,
                "phone": None,
            }
            return Response(data, status=status.HTTP_200_OK)

        return super().retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.get_object():
            raise ValidationError("Profile already exists. Use PUT/PATCH to update it.")
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    

class NonAdminUserListView(generics.ListAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user__is_superuser=False)

class UserDetailWithDealsView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get("pk")

        # Check if user exists
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get profile for the user (can be None)
        profile = UserProfile.objects.filter(user=user).first()
        profile_data = UserProfileSerializer(profile).data if profile else None

        # Get all deals for this user (can be empty)
        deals = PropertySubmission.objects.filter(user=user)
        deals_data = [
            {
                "id": d.id,
                "address": d.address,
                "land_type": d.land_type.name if d.land_type else None,
                "acreage": d.acreage,
                "asking_price": getattr(d, "asking_price", None),  # if field exists
                "status": d.status,
                "created_at": d.created_at,
            }
            for d in deals
        ]

        return Response({
            "user_profile": profile_data,
            "deals": deals_data
        }, status=status.HTTP_200_OK)

class UserLogoutView(generics.GenericAPIView):
    """User logout endpoint - blacklists the refresh token"""
    serializer_class = UserLogoutSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'Successfully logged out'
        }, status=status.HTTP_200_OK)
    


# LandType Views
class LandTypeListCreateView(generics.ListCreateAPIView):
    """List all land types or create a new land type"""
    queryset = LandType.objects.all()
    serializer_class = LandTypeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # Read for all, write for authenticated
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        land_type = serializer.save()
        
        return Response({
            'message': 'Land type created successfully',
            'data': LandTypeSerializer(land_type).data
        }, status=status.HTTP_201_CREATED)


class LandTypeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a specific land type"""
    queryset = LandType.objects.all()
    serializer_class = LandTypeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        land_type = serializer.save()
        
        return Response({
            'message': 'Land type updated successfully',
            'data': LandTypeSerializer(land_type).data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({
            'message': 'Land type deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


# Utility Views
class UtilityListCreateView(generics.ListCreateAPIView):
    """List all utilities or create a new utility"""
    queryset = Utility.objects.all()
    serializer_class = UtilitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        utility = serializer.save()
        
        return Response({
            'message': 'Utility created successfully',
            'data': UtilitySerializer(utility).data
        }, status=status.HTTP_201_CREATED)


class UtilityRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a specific utility"""
    queryset = Utility.objects.all()
    serializer_class = UtilitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        utility = serializer.save()
        
        return Response({
            'message': 'Utility updated successfully',
            'data': UtilitySerializer(utility).data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({
            'message': 'Utility deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


# AccessType Views
class AccessTypeListCreateView(generics.ListCreateAPIView):
    """List all access types or create a new access type"""
    queryset = AccessType.objects.all()
    serializer_class = AccessTypeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_type = serializer.save()
        
        return Response({
            'message': 'Access type created successfully',
            'data': AccessTypeSerializer(access_type).data
        }, status=status.HTTP_201_CREATED)


class AccessTypeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a specific access type"""
    queryset = AccessType.objects.all()
    serializer_class = AccessTypeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        access_type = serializer.save()
        
        return Response({
            'message': 'Access type updated successfully',
            'data': AccessTypeSerializer(access_type).data
        })
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({
            'message': 'Access type deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)