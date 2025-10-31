from rest_framework import serializers
from .models import FocusLog

class FocusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FocusLog
        # The RPi still only sends the 'status'
        # The 'session' will be added by the view
        fields = ['status']