from rest_framework import serializers
from .models import FocusLog

class FocusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FocusLog
        # We only need the RPi to send us the 'status'
        fields = ['status']