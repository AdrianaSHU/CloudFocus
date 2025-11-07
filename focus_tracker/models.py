from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid # For generating unique API keys

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    profile_picture = models.ImageField(
    upload_to='profile_pics/', 
    null=True, 
    blank=True
)
    has_seen_security_update = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


class Device(models.Model):
    """
    Represents a physical device/station (e.g., "Classroom RPi").
    Created by an admin.
    """
    name = models.CharField(max_length=100, default='Classroom RPi')
    device_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    def __str__(self):
        return self.name

class Session(models.Model):
    """
    Links a User to a Device for a period of time.
    Created when the user clicks "Start Session".
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} @ {self.device.name} (Active: {self.is_active})"

class FocusLog(models.Model):
    """
    A single data point, linked to an active session.
    """
    STATUS_CHOICES = [
        ('FOCUSED', 'Focused'),
        ('DISTRACTED', 'Distracted'),
        ('DROWSY', 'Drowsy'),
    ]
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.session.user.username} was {self.status} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
