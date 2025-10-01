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
from .models import LandType, Utility, AccessType, UserProfile
from .serializers import LandTypeSerializer, UtilitySerializer, AccessTypeSerializer
from ghl_accounts.utils import create_ghl_contact_for_user
from ghl_accounts.models import GHLAuthCredentials
from rest_framework.exceptions import ValidationError
from data_management_app.models import PropertySubmission

def get_tokens_for_user(user):
    """Generate JWT tokens for user"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class UserSignupView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    serializer_class = UserSignupSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # capture user + extra signup info
        user, phone, student_username, student_password = serializer.save()

        # Create GHL contact
        creds = GHLAuthCredentials.objects.last()
        if creds:
            ghl_contact_id = create_ghl_contact_for_user(
                creds.access_token,
                creds.location_id,
                user,
                phone=phone,
                student_username=student_username,
                student_password=student_password,
            )
            print("GHL contact created for user:", ghl_contact_id)
        else:
            print("No GHL credentials found for user signup")

        tokens = get_tokens_for_user(user)

        return Response({
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)

class UserLoginView(generics.GenericAPIView):
    """User login endpoint"""
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        tokens = get_tokens_for_user(user)
        
        return Response({
            'message': 'Login successful',
            'user': {
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