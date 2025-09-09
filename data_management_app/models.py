import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from accounts.models import BaseModel, LandType, Utility, AccessType


def validate_file_size(value):
    """Validate file size is under 10MB"""
    filesize = value.size
    if filesize > 10 * 1024 * 1024:  # 10MB
        raise ValidationError("File size cannot exceed 10MB")


def property_file_upload_path(instance, filename):
    """Generate upload path for property files"""
    # Create path: media/properties/{user_id}/{property_id}/{filename}
    ext = filename.split('.')[-1].lower()
    filename = f"{uuid.uuid4()}.{ext}"
    return f"properties/{instance.property.user.id}/{instance.property.id}/{filename}"


class PropertySubmission(BaseModel):
    """Model for property submissions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='property_submissions')
    address = models.CharField(max_length=500)
    land_type = models.ForeignKey(LandType, on_delete=models.CASCADE)
    acreage = models.DecimalField(max_digits=10, decimal_places=2)
    zoning = models.CharField(max_length=100)
    agreed_price = models.DecimalField(max_digits=12, decimal_places=2)
    utilities = models.ForeignKey(Utility, on_delete=models.CASCADE)
    access_type = models.ForeignKey(AccessType, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=20, decimal_places=16, null=True, blank=True)
    longitude = models.DecimalField(max_digits=20, decimal_places=16, null=True, blank=True)
    place_id = models.CharField(max_length=255, null=True, blank=True)  # optional
    
    # Additional characteristics
    property_characteristics = models.JSONField(default=list, blank=True)
    location_characteristics = models.JSONField(default=list, blank=True)
    
    llc_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()

    UNDER_CONTRACT_CHOICES = [('yes', 'Yes'), ('no', 'No')]
    under_contract = models.CharField(max_length=3, choices=UNDER_CONTRACT_CHOICES)
    parcel_id = models.CharField(max_length=255, blank=True, null=True)

    lot_size = models.DecimalField(max_digits=12, decimal_places=2)
    LOT_SIZE_UNITS = [('acres', 'Acres'), ('sqft', 'Square Feet')]
    lot_size_unit = models.CharField(max_length=10, choices=LOT_SIZE_UNITS)

    EXIT_STRATEGY_CHOICES = [
        ('infill', 'Infill Lot Development'),
        ('flip', 'Buy & Flip'),
        ('subdivide', 'Subdivide & Sell'),
        ('seller_financing', 'Seller Financing'),
        ('rezoning', 'Entitlement/Rezoning'),
        ('mobile_home', 'Mobile Home Lot'),
    ]
    exit_strategy = models.CharField(max_length=30, choices=EXIT_STRATEGY_CHOICES)

    extra_notes = models.TextField(blank=True)

    
    # Status tracking
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review_with_buyer', 'Under review with Buyer'),
        ('buyer_approved', 'Buyer Approved'),
        ('buyer_rejected', 'Buyer Rejected'),
        ('mls_pending', 'MLS Listing - Pending'),
        ('mls_active', 'MLS Active Listing'),
        ('sold', 'Sold Deal'),
        ('canceled', 'Canceled Deal'),
    ]

    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='submitted')
    
    buyer_rejected_notes = models.TextField(blank=True, null=True)
    
    # Admin fields
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_properties')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'property_submissions'
        verbose_name = 'Property Submission'
        verbose_name_plural = 'Property Submissions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.address} - {self.user.username}"
    
    @property
    def total_files_count(self):
        return self.files.count()


class PropertyFile(BaseModel):
    """Model for property-related files"""
    FILE_TYPE_CHOICES = [
        ('image', 'Image (JPG/PNG)'),
        ('pdf', 'PDF Document'),
        ('video', 'Video (MP4)'),
        ('kml', 'KML File'),
        ('cad', 'CAD File'),
        ('other', 'Other'),
    ]
    
    property = models.ForeignKey(PropertySubmission, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(
        upload_to=property_file_upload_path,
        validators=[
            validate_file_size,
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'pdf', 'mp4', 'kml', 'dwg', 'dxf', 'step', 'stp']
            )
        ]
    )
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    original_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    description = models.CharField(max_length=255, blank=True)
    
    class Meta:
        db_table = 'property_files'
        verbose_name = 'Property File'
        verbose_name_plural = 'Property Files'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.original_name} - {self.property.address}"
    
    def save(self, *args, **kwargs):
        if self.file:
            # Auto-detect file type based on extension
            ext = self.file.name.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png']:
                self.file_type = 'image'
            elif ext == 'pdf':
                self.file_type = 'pdf'
            elif ext == 'mp4':
                self.file_type = 'video'
            elif ext == 'kml':
                self.file_type = 'kml'
            elif ext in ['dwg', 'dxf', 'step', 'stp']:
                self.file_type = 'cad'
            else:
                self.file_type = 'other'
            
            # Store original filename and size
            if not self.original_name:
                self.original_name = self.file.name
            self.file_size = self.file.size
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Delete the actual file when the record is deleted
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)




# models.py

from django.db import models
from django.contrib.auth import get_user_model
from .models import PropertySubmission  # Assuming PropertySubmission is in the same app's models.py

User = get_user_model()

class ConversationMessage(models.Model):
    """Model for a message within a property-specific conversation."""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    property_submission = models.ForeignKey(PropertySubmission, on_delete=models.CASCADE, related_name='conversation_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']
        verbose_name = "Conversation Message"
        verbose_name_plural = "Conversation Messages"

    def __str__(self):
        return f"Message from {self.sender.username} on {self.property_submission.id} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"