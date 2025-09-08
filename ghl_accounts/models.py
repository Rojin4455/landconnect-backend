from django.db import models

# Create your models here.

class GHLAuthCredentials(models.Model):
    user_id = models.CharField(max_length=255, null=True, blank=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_in = models.IntegerField()
    scope = models.TextField(null=True, blank=True)
    user_type = models.CharField(max_length=50, null=True, blank=True)
    company_id = models.CharField(max_length=255, null=True, blank=True)
    location_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.user_id} - {self.company_id} - {self.location_id}"