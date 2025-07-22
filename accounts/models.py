from django.db import models

class BaseModel(models.Model):
    """Abstract base model with common fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class LandType(BaseModel):
    """Model for different types of land"""
    value = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    
    class Meta:
        db_table = 'land_types'
        verbose_name = 'Land Type'
        verbose_name_plural = 'Land Types'
        ordering = ['display_name']
    
    def __str__(self):
        return self.display_name


class Utility(BaseModel):
    """Model for different utilities"""
    value = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    
    class Meta:
        db_table = 'utilities'
        verbose_name = 'Utility'
        verbose_name_plural = 'Utilities'
        ordering = ['display_name']
    
    def __str__(self):
        return self.display_name


class AccessType(BaseModel):
    """Model for different access types"""
    value = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    
    class Meta:
        db_table = 'access_types'
        verbose_name = 'Access Type'
        verbose_name_plural = 'Access Types'
        ordering = ['display_name']
    
    def __str__(self):
        return self.display_name
