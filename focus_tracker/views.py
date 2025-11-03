from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Device, Session, FocusLog # Make sure Device is imported
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
import uuid 
from rest_framework.decorators import api_view 

from datetime import timedelta 

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
        # 1. Get the API key from the request headers
        api_key = request.headers.get('API-Key')
        if not api_key:
            return Response(
                {'error': 'API-Key header is required.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 2. Find the *Device* (not the user)
        try:
            device = Device.objects.get(api_key=api_key)
        except Device.DoesNotExist:
            return Response(
                {'error': 'Invalid API-Key. This device is not registered.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 3. Find the *active session* for this device
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

        # 4. Validate and save the data
        serializer = FocusLogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(session=active_session)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --- Register View ---
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

# --- Other Views  ---
def home_view(request):
    """ The main landing page. """
    return render(request, 'home.html')

def is_supervisor(user):
    return user.is_authenticated and user.is_staff

def about_view(request):
    """ Renders the 'About' page. """
    return render(request, 'about.html')

def contact_view(request):
    """ Renders the 'Contact Us' page and handles form submission. """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            from_email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            try:
                log_dir = os.path.join(settings.BASE_DIR, 'contact_logs')
                os.makedirs(log_dir, exist_ok=True)
                now_str = timezone.now().strftime('%Y-%m-%d_%H-%M-%S')
                filename = f"{now_str}_{from_email}.txt"
                file_path = os.path.join(log_dir, filename)
                file_content = (
                    f"From: {name} <{from_email}>\n"
                    f"Date: {timezone.now().isoformat()}\n"
                    f"Subject: {subject}\n"
                    f"----------------------------------\n\n"
                    f"{message}"
                )
                with open(file_path, 'w') as f:
                    f.write(file_content)
            except Exception as e:
                print(f"Error saving contact email to file: {e}")

            html_message = (
                f"<b>New message from:</b> {name} ({from_email})<br>"
                f"<b>Subject:</b> {subject}<br>"
                f"<hr>"
                f"<p>{message.replace(chr(10), '<br>')}</p>"
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
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST, 
            request.FILES, 
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

# --- (2)  dashboard_view ---
@login_required
def dashboard_view(request):
    """ 
    The main dashboard, now filtering for the last 7 days.
    """
    
    # ---  Calculate 7 days ago ---
    history = timezone.now() - timedelta(days=7)
    
    active_session = Session.objects.filter(
        user=request.user, 
        is_active=True
    ).first() 
    
    all_devices = Device.objects.all()
    
    # ---  Filter logs for last 7 days ---
    logs = list(FocusLog.objects.filter(
        session__user=request.user,
        timestamp__gte=history  # <-- Filter added
    ).order_by('timestamp'))
    
    # Get latest log (for sensors) - this query is fine
    latest_log = FocusLog.objects.filter(session__user=request.user).order_by('-timestamp').first()

    # This calculation now correctly uses the 7-day log data
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
        'latest_log': latest_log 
    }
    return render(request, 'dashboard.html', context)

# --- (3)  supervisor_user_detail_view ---
@user_passes_test(is_supervisor)
def supervisor_user_detail_view(request, user_id):
    """
    Shows the detailed dashboard for a specific user, filtered for 7 days.
    """
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('supervisor_dashboard')
        
    # ---  Calculate 7 days ago ---
    history = timezone.now() - timedelta(days=7)

    # ---  Filter logs for last 7 days ---
    logs = list(FocusLog.objects.filter(
        session__user=target_user,
        timestamp__gte=history # <-- Filter added
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
        'target_user': target_user,
        'chart_data_json': json.dumps(chart_data),
        'focused_percent': focused_percent,
        'distracted_percent': distracted_percent,
        'drowsy_percent': drowsy_percent,
    }
    return render(request, 'supervisor_user_detail.html', context)

# --- (4)  get_live_dashboard_data ---
@api_view(['GET'])
@login_required
def get_live_dashboard_data(request):
    """
    A lightweight API endpoint to be polled.
    Returns stats from the last 7 days.
    """
    
    # --- NEW: Calculate 7 days ago ---
    history = timezone.now() - timedelta(days=7)
    
    # ---  Filter logs for last 7 days ---
    logs = list(FocusLog.objects.filter(
        session__user=request.user,
        timestamp__gte=history # <-- Filter added
    ))
    
    # latest_log query is fine, it just shows current conditions
    latest_log = FocusLog.objects.filter(session__user=request.user).order_by('-timestamp').first()

    # This calculation now correctly uses the 7-day log data
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

    latest_temp = None
    latest_humidity = None
    if latest_log:
        latest_temp = latest_log.temperature
        latest_humidity = latest_log.humidity

    data = {
        'focused_percent': round(focused_percent, 0),
        'distracted_percent': round(distracted_percent, 0),
        'drowsy_percent': round(drowsy_percent, 0),
        'latest_temp': latest_temp,
        'latest_humidity': latest_humidity,
    }
    
    return Response(data)

# --- Session Views ---
@user_passes_test(is_supervisor)
def supervisor_dashboard_view(request):
    all_users = User.objects.filter(is_staff=False)
    context = {
        'users': all_users
    }
    return render(request, 'supervisor_dashboard.html', context)

@login_required
@require_POST
def start_session_view(request, device_id):
    try:
        device_to_start = Device.objects.get(id=device_id)
        
        Session.objects.filter(user=request.user, is_active=True).update(
            is_active=False, 
            end_time=timezone.now()
        )
        Session.objects.filter(device=device_to_start, is_active=True).update(
            is_active=False, 
            end_time=timezone.now()
        )
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
    try:
        active_session = Session.objects.get(user=request.user, is_active=True)
        active_session.is_active = False
        active_session.end_time = timezone.now()
        active_session.save()
        messages.info(request, "Your session has been ended.")
    except Session.DoesNotExist:
        messages.error(request, "You have no active session to end.")
        
    return redirect('dashboard')

