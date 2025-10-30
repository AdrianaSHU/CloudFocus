from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Device
from .serializers import FocusLogSerializer
from django.contrib.auth.decorators import login_required, user_passes_test
import json
from collections import Counter
from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import CustomUserCreationForm
from .forms import UserUpdateForm, ProfileUpdateForm
from django.contrib.auth.models import User

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
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Device.objects.create(owner=user, name=f"{user.username}'s RPi")
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
        
    return render(request, 'register.html', {'form': form})

def home_view(request):
    """ The main landing page. """
    return render(request, 'home.html')

# --- This is a check function ---
def is_supervisor(user):
    # Checks if the user is logged in AND is a staff member
    return user.is_authenticated and user.is_staff

@login_required
def dashboard_view(request):
    try:
        user_device = request.user.device
        api_key = user_device.api_key
        logs = list(user_device.logs.all().order_by('timestamp')) # <-- (2) Make it a list
        
    except AttributeError:
        api_key = "No device found. Please contact support."
        logs = []

    # --- (3) Add this whole calculation block ---
    total_logs = len(logs)
    if total_logs > 0:
        status_counts = Counter([log.status for log in logs])
        focused_percent = (status_counts.get('FOCUSED', 0) / total_logs) * 100
        distracted_percent = (status_counts.get('DISTRACTED', 0) / total_logs) * 100
        drowsy_percent = (status_counts.get('DROWSY', 0) / total_logs) * 100
    else:
        focused_percent = 0
        distracted_percent = 0
        drowsy_percent = 0
    # --- End of new block ---

    status_map = {'FOCUSED': 2, 'DISTRACTED': 1, 'DROWSY': 0}
    chart_data = [
        {'x': log.timestamp.isoformat(), 'y': status_map.get(log.status, 1)} 
        for log in logs
    ]
    
    context = {
        'api_key': api_key,
        'chart_data_json': json.dumps(chart_data),
        
        # --- (4) Add these to the context ---
        'focused_percent': focused_percent,
        'distracted_percent': distracted_percent,
        'drowsy_percent': drowsy_percent,
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

@login_required
def profile_view(request):
    # Handles updating the user's profile information.
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST, 
            request.FILES, # This handles the image upload
            instance=request.user.profile
        )
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')

    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    
    return render(request, 'profile.html', context)

@user_passes_test(is_supervisor) # This decorator protects the page
def supervisor_dashboard_view(request):
    """
    Shows a list of all non-supervisor users.
    """
    # Get all users who are NOT staff, so supervisors don't see themselves
    all_users = User.objects.filter(is_staff=False)
    
    context = {
        'users': all_users
    }
    return render(request, 'supervisor_dashboard.html', context)


@user_passes_test(is_supervisor) # Protect this page too
def supervisor_user_detail_view(request, user_id):
    """
    Shows the detailed dashboard for a specific user.
    """
    try:
        # Get the specific user the supervisor wants to see
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('supervisor_dashboard')

    # --- This is the same logic from your normal dashboard_view ---
    try:
        user_device = target_user.device
        logs = list(user_device.logs.all().order_by('timestamp'))
    except AttributeError:
        logs = []

    total_logs = len(logs)
    if total_logs > 0:
        status_counts = Counter([log.status for log in logs])
        focused_percent = (status_counts.get('FOCUSED', 0) / total_logs) * 100
        distracted_percent = (status_counts.get('DISTRACTED', 0) / total_logs) * 100
        drowsy_percent = (status_counts.get('DROWSY', 0) / total_logs) * 100
    else:
        focused_percent = 0
        distracted_percent = 0
        drowsy_percent = 0

    status_map = {'FOCUSED': 2, 'DISTRACTED': 1, 'DROWSY': 0}
    chart_data = [
        {'x': log.timestamp.isoformat(), 'y': status_map.get(log.status, 1)} 
        for log in logs
    ]
    # --- End of dashboard logic ---

    context = {
        'target_user': target_user, # Pass the user to the template
        'chart_data_json': json.dumps(chart_data),
        'focused_percent': focused_percent,
        'distracted_percent': distracted_percent,
        'drowsy_percent': drowsy_percent,
    }
    return render(request, 'supervisor_user_detail.html', context)
