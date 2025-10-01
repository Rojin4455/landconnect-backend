from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication endpoints
    path('signup/', views.UserSignupView.as_view(), name='user-signup'),
    path('login/', views.UserLoginView.as_view(), name='user-login'),
    path('admin/login/', views.AdminLoginView.as_view(), name='admin-login'),
    path('logout/', views.UserLogoutView.as_view(), name='user-logout'),
    
    # Token refresh
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('users/', views.NonAdminUserListView.as_view(), name='non-admin-user-list'),
    path("users/<int:pk>/details/", views.UserDetailWithDealsView.as_view(), name="user-details-with-deals"),
    
    # User profile
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('land-types/', views.LandTypeListCreateView.as_view(), name='landtype-list-create'),
    path('land-types/<int:pk>/', views.LandTypeRetrieveUpdateDestroyView.as_view(), name='landtype-detail'),
    
    # Utility endpoints
    path('utilities/', views.UtilityListCreateView.as_view(), name='utility-list-create'),
    path('utilities/<int:pk>/', views.UtilityRetrieveUpdateDestroyView.as_view(), name='utility-detail'),
    
    # AccessType endpoints
    path('access-types/', views.AccessTypeListCreateView.as_view(), name='accesstype-list-create'),
    path('access-types/<int:pk>/', views.AccessTypeRetrieveUpdateDestroyView.as_view(), name='accesstype-detail'),
]