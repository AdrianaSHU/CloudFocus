from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Device
from .serializers import FocusLogSerializer
# We will add more imports later for the web pages

# --- API View ---

class LogFocusView(APIView):
    """
    API endpoint for the RPi to POST focus data.
    Requires 'API-Key' in the headers for authentication.
    """
    
    def post(self, request, *args, **kwargs):
        # 1. Get the API key from the request headers
        api_key = request.headers.get('API-Key')
        if not api_key:
            return Response(
                {'error': 'API-Key header is required.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 2. Find the device (and owner) with this key
        try:
            # We use .select_related('owner') for a more efficient
            # database query, as we know we'll need the owner.
            device = Device.objects.select_related('owner').get(api_key=api_key)
        except Device.DoesNotExist:
            return Response(
                {'error': 'Invalid API-Key.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 3. Validate and save the data
        serializer = FocusLogSerializer(data=request.data)
        if serializer.is_valid():
            # Save the log, associating it with the authenticated device
            # This automatically links it to the device's owner
            serializer.save(device=device)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # If data is bad (e.g., status="SLEEPING")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- Web Views (like dashboard, login) will be added below here ---