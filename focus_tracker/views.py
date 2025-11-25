# focus_tracker/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings 
from django.views.decorators.http import require_POST
from django.utils import timezone

import json
import os
import uuid 
from collections import Counter
from datetime import timedelta 

# --- Import Models & Forms ---
from .models import Device, Session, FocusLog
from .serializers import FocusLogSerializer
from .forms import (
    CustomUserCreationForm, 
    UserUpdateForm, 
    ProfileUpdateForm, 
    ContactForm
)
from .image_utils import handle_profile_picture_upload

# --- (1) IMPORT YOUR UTILS ---
from .dashboard_utils import get_dashboard_data


# ==========================================
#               API VIEWS
# ==========================================

class LogFocusView(APIView):
    """
    Receives data from the Python Script/Camera
    """
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
            # Handle edge case where db has multiple active sessions
            active_session = Session.objects.filter(device=device, is_active=True).last()

        serializer = FocusLogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(session=active_session)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@login_required
def get_live_dashboard_data(request):
    """
    Called by JS to update the dashboard in real-time.
    """
    try:
        # 1. Get calculations using the utility
        data = get_dashboard_data(request.user, request.GET)
        
        # 2. REMOVE the raw 'logs' list because QuerySets are not JSON serializable
        if 'logs' in data:
            del data['logs']
            
        return Response(data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==========================================
#           DASHBOARD & SESSION
# ==========================================

@login_required
def dashboard_view(request):
    """ 
    The main dashboard view.
    Handles: Data calculation, Chart preparation, and Table Pagination.
    """
    
    # 1. Get Data (Stats + Logs in Ascending Order for Chart)
    data = get_dashboard_data(request.user, request.GET)
    
    # 2. Extract logs and prepare for Table
    # The chart needs Old -> New. The table needs New -> Old.
    raw_logs = data.pop('logs') # Pop removes it from 'data' so we don't duplicate
    logs_for_table = list(reversed(raw_logs)) 
    
    # 3. Pagination Logic
    paginator = Paginator(logs_for_table, 10) # Show 10 logs per page
    page = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # 4. Get Active Session Info
    active_session = Session.objects.filter(user=request.user, is_active=True).first() 
    all_devices = Device.objects.all()
    
    # 5. Build Context
    context = {
        'active_session': active_session,
        'all_devices': all_devices,
        'page_obj': page_obj,  # Pass the paginated object
        **data # Unpack percentages, chart_json, dates, etc.
    }
    return render(request, 'dashboard.html', context)


@login_required
@require_POST
def start_session_view(request, device_id):
    try:
        device_to_start = Device.objects.get(id=device_id)
        
        # Close any existing sessions for this user or this device
        Session.objects.filter(user=request.user, is_active=True).update(
            is_active=False, end_time=timezone.now()
        )
        Session.objects.filter(device=device_to_start, is_active=True).update(
            is_active=False, end_time=timezone.now()
        )
        
        # Create new
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
        active_session = Session.objects.filter(user=request.user, is_active=True).first()
        if active_session:
            active_session.is_active = False
            active_session.end_time = timezone.now()
            active_session.save()
            messages.info(request, "Your session has been ended.")
        else:
            messages.error(request, "You have no active session to end.")
    except Exception as e:
        messages.error(request, f"Error ending session: {e}")
        
    return redirect('dashboard')


@login_required
@require_POST
def correct_log_view(request, log_id):
    """
    Allows user to correct a log entry (e.g., from 'Distracted' to 'Focused')
    """
    try:
        log_to_correct = get_object_or_404(FocusLog, id=log_id)

        # Security: User must own the session
        if log_to_correct.session.user != request.user:
            messages.error(request, "You do not have permission to change this log.")
            return redirect('dashboard')

        log_to_correct.status = 'FOCUSED'
        log_to_correct.save()
        messages.success(request, "Log successfully corrected to 'Focused'.")
        
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")

    return redirect('dashboard')


# ==========================================
#           SUPERVISOR & ADMIN
# ==========================================

def is_supervisor(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(is_supervisor)
def supervisor_dashboard_view(request):
    """
    Blind-to-Teacher Dashboard. Shows aggregated stats only.
    """
    participant_count = Session.objects.filter(is_active=True).values('user').distinct().count()
    logs = FocusLog.objects.filter(session__is_active=True)
    total_logs = logs.count()
    
    if total_logs > 0:
        focus_count = logs.filter(status='FOCUSED').count()
        distract_count = logs.filter(status='DISTRACTED').count()
        drowsy_count = logs.filter(status='DROWSY').count()
        
        focused_percent = (focus_count / total_logs) * 100
        distracted_percent = (distract_count / total_logs) * 100
        drowsy_percent = (drowsy_count / total_logs) * 100

        recent_logs = logs.order_by('-timestamp')[:100]
        status_map = {'DROWSY': 0, 'DISTRACTED': 1, 'FOCUSED': 2, 'NO FACE': None}
        
        chart_data = [
            {
                'x': log.timestamp.isoformat(), 
                'y': status_map.get(log.status)
            }
            for log in recent_logs if status_map.get(log.status) is not None
        ]
    else:
        focused_percent = 0
        distracted_percent = 0
        drowsy_percent = 0
        chart_data = []

    context = {
        'participant_count': participant_count,
        'total_logs': total_logs,
        'focused_percent': focused_percent,
        'distracted_percent': distracted_percent,
        'drowsy_percent': drowsy_percent,
        'chart_data_json': json.dumps(chart_data),
    }
    return render(request, 'supervisor_dashboard.html', context)


# ==========================================
#           USER ACCOUNTS & PAGES
# ==========================================

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

@login_required
def profile_view(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            image_file = request.FILES.get('profile_picture')
            if image_file:
                saved_file_name = handle_profile_picture_upload(
                    image_file, 
                    min_size=(256, 256),
                    use_azure=True 
                )
                request.user.profile.profile_picture.name = saved_file_name

            profile_form.save() 
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {'user_form': user_form, 'profile_form': profile_form}
    return render(request, 'profile.html', context)

def home_view(request):
    return render(request, 'home.html')

def about_view(request):
    return render(request, 'about.html')

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # (Your existing email logic here - omitted for brevity but keeping the flow)
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('home')
    else:
        form = ContactForm()
    return render(request, 'contact.html', {'form': form})