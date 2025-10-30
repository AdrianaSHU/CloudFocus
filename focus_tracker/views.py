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
from django.core.mail import send_mail
from django.conf import settings 

import os
from django.utils import timezone

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
            # Get the form data
            name = form.cleaned_data['name']
            from_email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            # --- 1. Save the email to a local file ---
            try:
                # Define the log directory path (at your project root)
                log_dir = os.path.join(settings.BASE_DIR, 'contact_logs')
                # Create the directory if it doesn't exist
                os.makedirs(log_dir, exist_ok=True)
                
                # Create a unique filename with a timestamp
                now_str = timezone.now().strftime('%Y-%m-%d_%H-%M-%S')
                filename = f"{now_str}_{from_email}.txt"
                file_path = os.path.join(log_dir, filename)
                
                # Format the file content
                file_content = (
                    f"From: {name} <{from_email}>\n"
                    f"Date: {timezone.now().isoformat()}\n"
                    f"Subject: {subject}\n"
                    f"----------------------------------\n\n"
                    f"{message}"
                )
                
                # Write the file
                with open(file_path, 'w') as f:
                    f.write(file_content)
                    
            except Exception as e:
                # If file saving fails, log it to the console but continue
                print(f"Error saving contact email to file: {e}")

            # --- 2. Send the email via SendGrid ---
            html_message = (
                f"<b>New message from:</b> {name} ({from_email})<br>"
                f"<b>Subject:</b> {subject}<br>"
                f"<hr>"
                f"<p>{message.replace(chr(10), '<br>')}</p>" # Replace newlines with <br>
            )
            
            try:
                send_mail(
                    subject=f"Contact Form: {subject}",
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    html_message=html_message,
                    fail_silently=False,
                )
                messages.success(request, 'Your message has been sent successfully!')
            
            except Exception as e:
                messages.error(request, 'Sorry, there was an error sending your message.')

            return redirect('home')
    else:
        form = ContactForm()
        
    return render(request, 'contact.html', {'form': form})