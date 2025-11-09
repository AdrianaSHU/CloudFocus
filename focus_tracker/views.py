# focus_tracker/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
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
import uuid 
from rest_framework.decorators import api_view
from datetime import timedelta 

# --- (1) IMPORT YOUR NEW UTILS ---
from .dashboard_utils import get_dashboard_data

# Import all forms
from .forms import (
    CustomUserCreationForm, 
    UserUpdateForm, 
    ProfileUpdateForm, 
    ContactForm
)

# --- API View (Unchanged) ---
class LogFocusView(APIView):
    def post(self, request, *args, **kwargs):
        api_key = request.headers.get('API-Key')
        if not api_key:
            return Response({'error': 'API-Key header is required.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            device = Device.objects.get(api_key=api_key)
        except Device.DoesNotExist:
            return Response({'error': 'Invalid API-Key. This device is not registered.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            active_session = Session.objects.get(device=device, is_active=True)
        except Session.DoesNotExist:
            return Response({'error': 'No active session found. Please "Start Session" on the website.'}, status=status.HTTP_403_FORBIDDEN)
        except Session.MultipleObjectsReturned:
            return Response({'error': 'Data conflict. Multiple active sessions found.'}, status=status.HTTP_409_CONFLICT)

        serializer = FocusLogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(session=active_session)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            profile_picture = form.cleaned_data.get('profile_picture')
            if profile_picture:
                user.profile.profile_picture.save(profile_picture.name, profile_picture)
                user.profile.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})



# --- Other Views (Unchanged) ---
def home_view(request):
    return render(request, 'home.html')

def is_supervisor(user):
    return user.is_authenticated and user.is_staff

def about_view(request):
    return render(request, 'about.html')

def contact_view(request):
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
                    f"From: {name} <{from_email}>\nDate: {timezone.now().isoformat()}\n"
                    f"Subject: {subject}\n----------------------------------\n\n{message}"
                )
                with open(file_path, 'w') as f:
                    f.write(file_content)
            except Exception as e:
                print(f"Error saving contact email to file: {e}")

            html_message = (
                f"<b>New message from:</b> {name} ({from_email})<br>"
                f"<b>Subject:</b> {subject}<br><hr><p>{message.replace(chr(10), '<br>')}</p>"
            )
            try:
                send_mail(
                    subject=f"Contact Form: {subject}", message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    html_message=html_message, fail_silently=False,
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
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            
            profile_picture = request.FILES.get('profile_picture')
            if profile_picture:
                request.user.profile.profile_picture.save(profile_picture.name, profile_picture)
            request.user.profile.save()

            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)
    context = {'user_form': user_form, 'profile_form': profile_form}
    return render(request, 'profile.html', context)



# --- (2) UPDATED dashboard_view ---
@login_required
def dashboard_view(request):
    """ 
    The main dashboard, now with period filters.
    """
    
    # --- NEW: Pass the request.GET to the util function ---
    # This gets all our stats (focused %, chart_data, etc.)
    # and also gets the 'start_date_str' and 'end_date_str'
    data = get_dashboard_data(request.user, request.GET)
    
    # Get session data (this is separate from the stats)
    active_session = Session.objects.filter(
        user=request.user, 
        is_active=True
    ).first() 
    all_devices = Device.objects.all()
    
    # Add all data to the context
    context = {
        'active_session': active_session,
        'all_devices': all_devices,
        **data # This unpacks all the keys from get_dashboard_data
    }
    return render(request, 'dashboard.html', context)


# --- (3) UPDATED supervisor_user_detail_view ---
@user_passes_test(is_supervisor)
def supervisor_user_detail_view(request, user_id):
    """
    Shows the detailed dashboard for a specific user, with period filters.
    """
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('supervisor_dashboard')
        
    # --- NEW: Pass the request.GET to the util function ---
    data = get_dashboard_data(target_user, request.GET)
    
    context = {
        'target_user': target_user,
        **data # This unpacks all the keys from get_dashboard_data
    }
    return render(request, 'supervisor_user_detail.html', context)


# --- (4) UPDATED get_live_dashboard_data ---
@api_view(['GET'])
@login_required
def get_live_dashboard_data(request):
    """
    A lightweight API endpoint to be polled.
    Returns stats from the user-selected time period.
    """
    
    # --- NEW: Pass the request.GET to the util function ---
    data = get_dashboard_data(request.user, request.GET)
    
    # We only need to return the keys that are being updated
    live_data = {
        'focused_percent': data['focused_percent'],
        'distracted_percent': data['distracted_percent'],
        'drowsy_percent': data['drowsy_percent'],
        'latest_temp': data['latest_temp'],
        'latest_humidity': data['latest_humidity'],
    }
    
    return Response(live_data)

# --- Session Views (Unchanged) ---
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