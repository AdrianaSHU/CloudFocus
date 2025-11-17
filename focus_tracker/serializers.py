from rest_framework import serializers
from .models import FocusLog

class FocusLogSerializer(serializers.ModelSerializer):
    """
    Serializes the data from the Raspberry Pi (the request.data)
    and maps it to the FocusLog model.
    """
    class Meta:
        model = FocusLog
        
        # --- (1) FIELDS ---
        # This list now includes ALL fields from the model.
        # This is because we want the API to RETURN the full
        # object after it's created.
        fields = [
            'id',
            'session',
            'timestamp',
            'status',
            'emotion_detected', # <-- Added this missing field
            'temperature',
            'humidity',
        ]
        
        # --- (2) READ_ONLY_FIELDS ---
        # This tells the serializer which fields are NOT
        # required in the incoming request from the Pi.
        #
        # 'id', 'session', and 'timestamp' are all set
        # by the server, not the Pi.
        read_only_fields = ['id', 'session', 'timestamp']