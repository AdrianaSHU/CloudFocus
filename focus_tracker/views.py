from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# Import all our models
from .models import Device, Session, FocusLog
from .serializers import FocusLogSerializer

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth import login

import json
from collections import Counter
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings 
from django.views.decorators.http import require_POST
import os
from django.utils import timezone
import uuid # Import uuid

# Import all forms at once
from .forms import (
    CustomUserCreationForm, 
    UserUpdateForm, 
    ProfileUpdateForm, 
    ContactForm
)


# --- API View  ---
class LogFocusView(APIView):
    """
    API endpoint for the RPi to POST focus data.
    This view uses the "Shared Device" (Check-In) model.
    """
    
    def post(self, request, *args, **kwargs):
        api_key = request.headers.get('API-Key')
        if not api_key:
            return Response(
                {'error': 'API-Key header is required.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            device = Device.objects.get(api_key=api_key)
        except Device.DoesNotExist:
            return Response(
                {'error': 'Invalid API-Key. This device is not registered.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            active_session = Session.objects.get(
                device=device, 
                is_active=True
            )
        except Session.DoesNotExist:
            return Response(
                {'error': 'No active session found for this device. Please "Start Session" on the website.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Session.MultipleObjectsReturned:
            return Response(
                {'error': 'Data conflict. Multiple active sessions found.'}, 
                status=status.HTTP_409_CONFLICT
            )

        serializer = FocusLogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(session=active_session)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def register_view(request):
    """ Handles user registration. """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        
        if form.is_valid():
            user = form.save()
            
            profile_picture = form.cleaned_data.get('profile_picture')
            
            if profile_picture:
                user.profile.profile_picture = profile_picture
                user.profile.save()
            
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
    """ 
    The main dashboard for the "Shared Device" model.
    Shows session controls and the user's personal data.
    """
    active_session = Session.objects.filter(
        user=request.user, 
        is_active=True
    ).first() # .first() safely returns one or None
    
    all_devices = Device.objects.all()
    
    logs = list(FocusLog.objects.filter(
        session__user=request.user
    ).order_by('timestamp'))

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
    
    context = {
        'active_session': active_session,
        'all_devices': all_devices,
        'chart_data_json': json.dumps(chart_data),
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


@user_passes_test(is_supervisor)
def supervisor_user_detail_view(request, user_id):
    """
    Shows the detailed dashboard for a specific user,
    using the new "Session" data model.
    """
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('supervisor_dashboard')

    # Get all logs from all of this user's sessions
    logs = list(FocusLog.objects.filter(
        session__user=target_user
    ).order_by('timestamp'))

    # --- This calculation logic is the same as before ---
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

    context = {
        'target_user': target_user,
        'chart_data_json': json.dumps(chart_data),
        'focused_percent': focused_percent,
        'distracted_percent': distracted_percent,
        'drowsy_percent': drowsy_percent,
    }
    return render(request, 'supervisor_user_detail.html', context)

@login_required
@require_POST # Ensures this can only be called by our form button
def start_session_view(request, device_id):
    """
    Starts a new session for the logged-in user on a specific device.
    """
    try:
        device_to_start = Device.objects.get(id=device_id)
        
        # --- Business Logic ---
        # 1. End any other active sessions for THIS USER
        Session.objects.filter(user=request.user, is_active=True).update(
            is_active=False, 
            end_time=timezone.now()
        )
        
        # 2. End any other active sessions on THIS DEVICE (kicks off other user)
        Session.objects.filter(device=device_to_start, is_active=True).update(
            is_active=False, 
            end_time=timezone.now()
        )
        
        # 3. Create the new session
        Session.objects.create(
            user=request.user,
            device=device_to_start,
            is_active=True
        )
        
        messages.success(request, f"Session started on {device_to_start.name}.")
        
    except Device.DoesNotExist:
        messages.error(request, "Device not found.")
    
    return redirect('dashboard')


@login_required
@require_POST
def end_session_view(request):
    """
    Ends the user's current active session.
    """
    try:
        active_session = Session.objects.get(user=request.user, is_active=True)
        active_session.is_active = False
        active_session.end_time = timezone.now()
        active_session.save()
        messages.info(request, "Your session has been ended.")
    except Session.DoesNotExist:
        messages.error(request, "You have no active session to end.")
        
    return redirect('dashboard')