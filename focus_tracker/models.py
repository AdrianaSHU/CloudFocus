from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid # For generating unique API keys

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # We'll use Azure Blob Storage to store these files.
    # profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    profile_picture = models.ImageField(
        upload_to='profile_pics/', 
        default='profile_pics/default.png', # Add a default image
        null=True, 
        blank=True
    )

    def __str__(self):
        return self.user.username

# These two functions (called "signals") automatically create and save
# a Profile whenever a new User is created.
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class Device(models.Model):
    """ 
    Represents a physical RPi device, owned by a user.
    We use OneToOneField for a strict single-device-per-user link.
    """
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='device')
    
    name = models.CharField(max_length=100, default='My Raspberry Pi')
    device_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # This is the secret key your RPi will use to authenticate
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    def __str__(self):
        return f"{self.name} ({self.owner.username})"

class FocusLog(models.Model):
    STATUS_CHOICES = [
        ('FOCUSED', 'Focused'),
        ('DISTRACTED', 'Distracted'),
        ('DROWSY', 'Drowsy'),
    ]
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def __str__(self):
        return f"{self.device.owner.username} was {self.status} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp'] # Show newest logs first