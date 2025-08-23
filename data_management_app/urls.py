from django.urls import path
from . import views

urlpatterns = [    
    # Property Submission endpoints
    path('properties/', views.PropertySubmissionCreateView.as_view(), name='property-create'),
    path('properties/list/', views.PropertySubmissionListView.as_view(), name='property-list'),
    path('properties/list-all/', views.AllPropertySubmissionListView.as_view(), name='property-list'),
    path('properties/list/<int:pk>/', views.UserPropertySubmissionListView.as_view(), name='property-list'),

    path('properties/<int:pk>/', views.PropertySubmissionDetailView.as_view(), name='property-detail'),

    path('property-detail/<int:pk>/', views.PropertyDetailView.as_view(), name='property-detail'),
    path('properties/<int:pk>/update/', views.PropertySubmissionUpdateView.as_view(), name='property-update'),
    path('properties/<int:pk>/delete/', views.PropertySubmissionDeleteView.as_view(), name='property-delete'),
    path('properties/<int:pk>/status/', views.PropertyStatusUpdateView.as_view(), name='property-status-update'),

    # Property File endpoints
    path('properties/<int:property_id>/files/', views.PropertyFileCreateView.as_view(), name='property-files-create'),
    path('files/<int:pk>/delete/', views.PropertyFileDeleteView.as_view(), name='property-file-delete'),
    
    # Admin endpoints
    path('admin/properties/', views.AdminPropertySubmissionListView.as_view(), name='admin-property-list'),


    path('conversations/<int:property_submission_id>/', views.ConversationMessageListView.as_view(), name='conversation-list'),
    # POST /api/conversations/<property_submission_id>/send/
    path('conversations/<int:property_submission_id>/send/', views.ConversationMessageCreateView.as_view(), name='conversation-send'),
    
    path('properties/<int:property_id>/matching-buyers/', 
         views.PropertyMatchingBuyersView.as_view(), 
         name='property-matching-buyers'),
    
    path('properties/<int:property_id>/matching-buyers/<int:buyer_id>/', 
         views.PropertyMatchingBuyerDetailView.as_view(), 
         name='property-matching-buyer-detail'),
]