from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import datetime
import uuid

# The Profile model is linked to the built-in User model
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Profile Picture is stored in Azure Blob Storage
    profile_picture = models.ImageField(
        upload_to='profile_pics', 
        null=True, 
        blank=True
    )
    has_seen_security_update = models.BooleanField(default=False)
    
    # Critical ethical field required to prove informed consent (Appendix A2)
    consent_agreed = models.BooleanField(default=False, verbose_name="Agreed to Privacy Policy")
    consent_date = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Signal to automatically create a Profile instance when a new User is created."""
    if created:
        Profile.objects.create(user=instance)

# The Device model is essential for the Edge Device Layer
class Device(models.Model):
    name = models.CharField(max_length=100, default='Raspberry Pi Unit')
    device_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # API key enables secure authentication (NFR2) for data logging
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # 'last_seen' implements the Heartbeat mechanism for device health monitoring
    last_seen = models.DateTimeField(null=True, blank=True)

    @property
    def is_active(self):
        """Returns True if the device has been seen in the last 2 minutes."""
        if not self.last_seen:
            return False
        return (timezone.now() - self.last_seen) < datetime.timedelta(minutes=2)

    def __str__(self):
        return self.name

# The Session model links a User to a Device over a defined period.
class Session(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} @ {self.device.name} (Active: {self.is_active})"

# FocusLog is the core data model fulfilling FR5 (Data Storage)
class FocusLog(models.Model):
    # Statuses derived from Edge AI classification (FR3)
    STATUS_CHOICES = [
        ('FOCUSED', 'Focused'),
        ('DISTRACTED', 'Distracted'),
        ('DROWSY', 'Drowsy'),
        ('NO FACE', 'No Face'),
    ]
    
    # Emotion categories based on CNN model output
    EMOTION_CHOICES = [
        ('Neutral', 'Neutral'), 
        ('Happy', 'Happy'), 
        ('Sad', 'Sad'), 
        ('Angry', 'Angry'),
        ('Surprise', 'Surprise'), 
        ('Fear', 'Fear'), 
        ('Disgust', 'Disgust'),
        ('No Face', 'No Face'), 
        ('No ROI', 'No ROI'),
    ]
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Flag enables user to correct misclassifications (Self-reflection tool)
    manual_correction = models.BooleanField(default=False, verbose_name="Manually Corrected")

    emotion_detected = models.CharField(
        max_length=20, 
        choices=EMOTION_CHOICES,
        default='No Face'
    )
    
    # Environmental data (optional sensor integration)
    temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.session.user.username} was {self.status} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']