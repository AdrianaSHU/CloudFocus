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
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings 
from django.views.decorators.http import require_POST
import os
from django.utils import timezone
from .image_utils import handle_profile_picture_upload

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

            image_file = request.FILES.get('profile_picture')
            if image_file:
                # Choose storage: True = Azure, False = local
                saved_file_name = handle_profile_picture_upload(
                    image_file, 
                    min_size=(256, 256),
                    use_azure=True  # <-- change to False if you want local storage
                )
                request.user.profile.profile_picture.name = saved_file_name

            profile_form.save()  # saves profile instance
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


# We are removing supervisor_user_detail_view
# It violates the "blind to the teacher" mitigation.
# @user_passes_test(is_supervisor)
# def supervisor_user_detail_view(request, user_id):



# --- (4) UPDATED get_live_dashboard_data ---
@api_view(['GET'])
@login_required
def get_live_dashboard_data(request):
    """
    FIXED: This view now correctly fetches data using the
    dashboard util, just like the main dashboard view.
    """
    try:
        # (1) Get the data using the same util as the dashboard
        # This gets percentages, chart data, temps, etc.
        data = get_dashboard_data(request.user, request.GET)
        
        # (2) We can't return the raw 'logs' object (model objects) 
        # in JSON, so we safely remove it.
        if 'logs' in data:
            del data['logs']
            
        # (3) Return the whole data dictionary as JSON
        return Response(data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# --- REWRITE THIS VIEW ---
@user_passes_test(is_supervisor)
def supervisor_dashboard_view(request):
    """
    ETHICAL FIX:
    This view is now "blind" to the supervisor.
    It shows ONLY aggregated, anonymous class-level data.
    It no longer shows a list of students.
    """
    
    # --- (A) Get participant count (Ethical Mitigation) ---
    # This finds the number of *distinct* users who have an active session
    participant_count = Session.objects.filter(is_active=True).values('user').distinct().count()
    
    # --- (B) Get aggregated stats ---
    # Get all logs from all active sessions
    logs = FocusLog.objects.filter(session__is_active=True)
    
    total_logs = logs.count()
    
    if total_logs > 0:
        # Calculate percentages
        focus_count = logs.filter(status='FOCUSED').count()
        distract_count = logs.filter(status='DISTRACTED').count()
        drowsy_count = logs.filter(status='DROWSY').count()
        
        focused_percent = (focus_count / total_logs) * 100
        distracted_percent = (distract_count / total_logs) * 100
        drowsy_percent = (drowsy_count / total_logs) * 100

        # --- (C) Get data for a simple chart ---
        # (This is a simplified version of your dashboard util)
        # We are just showing the last 100 logs as an example
        recent_logs = logs.order_by('-timestamp')[:100]
        
        # We map status to a number for the chart
        status_map = {'DROWSY': 0, 'DISTRACTED': 1, 'FOCUSED': 2, 'NO FACE': None}
        
        chart_data = [
            {
                'x': log.timestamp.isoformat(), 
                'y': status_map.get(log.status)
            }
            for log in recent_logs if status_map.get(log.status) is not None
        ]
        
    else:
        # Default values if no one is active
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


@login_required
@require_POST # This view only accepts POST requests
def correct_log_view(request, log_id):
    """
    Handles the 'This was wrong' feedback button.
    Finds the log, verifies the user owns it, and updates its
    status to 'FOCUSED'.
    """
    try:
        # Find the log the user clicked on
        log_to_correct = get_object_or_404(FocusLog, id=log_id)

        # --- SECURITY CHECK ---
        # Verify that the user clicking the button is the
        # user who owns the session this log belongs to.
        if log_to_correct.session.user != request.user:
            # If not, deny permission
            messages.error(request, "You do not have permission to change this log.")
            return redirect('dashboard')

        # --- SUCCESS ---
        # Update the log's status
        log_to_correct.status = 'FOCUSED'
        # Note: We leave 'emotion_detected' as-is, so you can 
        # later analyze how often 'Angry' was misclassified.
        
        log_to_correct.save()

        messages.success(request, "Log successfully corrected to 'Focused'.")
        
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")

    # Send the user back to the dashboard
    return redirect('dashboard')



@login_required
def dashboard_view(request):
    """ 
    The main dashboard, now with period filters and pagination.
    """
    # --- Data Retrieval ---
    data = get_dashboard_data(request.user, request.GET)
    logs = data.pop('logs') # Get the raw logs list and remove it from 'data' context
    
    # --- Pagination Logic ---
    # We will show 15 logs per page
    paginator = Paginator(logs, 15) 
    
    # Get the page number from the URL, defaulting to 1
    page = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page_obj = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        page_obj = paginator.page(paginator.num_pages)
    
    # --- Context Assembly ---
    active_session = Session.objects.filter(
        user=request.user, 
        is_active=True
    ).first() 
    all_devices = Device.objects.all()
    
    context = {
        'active_session': active_session,
        'all_devices': all_devices,
        'page_obj': page_obj,  # <-- NEW: The paginated log results
        **data # This unpacks all the other keys (percentages, dates, etc.)
    }
    return render(request, 'dashboard.html', context)