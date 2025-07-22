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
    asking_price = models.DecimalField(max_digits=12, decimal_places=2)
    estimated_aev = models.DecimalField(max_digits=12, decimal_places=2, help_text="Estimated Assessed Evaluated Value")
    development_costs = models.DecimalField(max_digits=12, decimal_places=2)
    utilities = models.ForeignKey(Utility, on_delete=models.CASCADE)
    access_type = models.ForeignKey(AccessType, on_delete=models.CASCADE)
    topography = models.TextField()
    environmental_factors = models.TextField()
    nearest_attraction = models.CharField(max_length=255)
    description = models.TextField()
    
    # Status tracking
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    
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

    class Meta:
        ordering = ['timestamp']
        verbose_name = "Conversation Message"
        verbose_name_plural = "Conversation Messages"

    def __str__(self):
        return f"Message from {self.sender.username} on {self.property_submission.id} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"