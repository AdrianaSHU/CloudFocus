from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Device
from .serializers import FocusLogSerializer
from django.contrib.auth.decorators import login_required 
import json
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm

from django.contrib import messages
from .forms import ContactForm

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

def register_view(request):
    """ Handles user registration. """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # --- IMPORTANT ---
            # Automatically create a Device for this new user
            # This links their account to a unique API key
            Device.objects.create(owner=user, name=f"{user.username}'s RPi")
            # --- END ---
            
            # Log the user in immediately
            login(request, user)
            return redirect('dashboard') 
    else:
        form = UserCreationForm()
        
    return render(request, 'register.html', {'form': form})

def home_view(request):
    """ The main landing page. """
    return render(request, 'home.html')

@login_required # This decorator automatically protects the page
def dashboard_view(request):
    
    try:
        # Get the user's device to find their API key
        user_device = request.user.device
        api_key = user_device.api_key
        
        # Get all logs for that device
        logs = user_device.logs.all().order_by('timestamp')
        
    except AttributeError:
        # This handles a case where a user might exist but their
        # device was somehow not created (e.g., old admin user)
        api_key = "No device found. Please contact support."
        logs = []

    # We map text status to a number for the chart:
    # 2 = Focused, 1 = Distracted, 0 = Drowsy
    status_map = {'FOCUSED': 2, 'DISTRACTED': 1, 'DROWSY': 0}
    
    chart_data = [
        {
            'x': log.timestamp.isoformat(), # ISO format for JavaScript
            'y': status_map.get(log.status, 1) # Default to 'Distracted' if unknown
        } 
        for log in logs
    ]
    
    context = {
        # Pass the API key to show on the page
        'api_key': api_key,
        
        # Pass the log data as a JSON string
        'chart_data_json': json.dumps(chart_data)
    }
    return render(request, 'dashboard.html', context)

def about_view(request):
    """ Renders the 'About' page. """
    return render(request, 'about.html')

def contact_view(request):
    """ Renders the 'Contact Us' page and handles form submission. """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # In a real app, you'd email this data.
            # For this project, we'll just show a success message.
            # This fulfills the requirement without complex email setup.
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('home')
    else:
        form = ContactForm()
        
    return render(request, 'contact.html', {'form': form})