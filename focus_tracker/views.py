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
from django.core.mail import EmailMessage
from django.conf import settings 
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.http import JsonResponse
import logging
import json
import os
import uuid 
from collections import Counter
from datetime import timedelta 
import google.generativeai as genai
from django.db.models import Count, Q

# --- Import Models & Forms ---
from .models import Device, Session, FocusLog, Profile
from .serializers import FocusLogSerializer
from .forms import (
    CustomUserCreationForm, 
    UserUpdateForm, 
    ProfileUpdateForm, 
    ContactForm
)
from .image_utils import handle_profile_picture_upload

# --- IMPORT UTILS ---
from .dashboard_utils import get_dashboard_data


# ==========================================
#               API VIEWS
# ==========================================

class LogFocusView(APIView):
    """
    Receives data from the Python Script/Camera.
    1. Updates Device 'last_seen' (Heartbeat).
    2. Saves the Log.
    3. Auto-ends session if 'NO FACE' persists for 30 minutes.
    """
    def post(self, request, *args, **kwargs):
        # 1. Validate API Key
        api_key = request.headers.get('API-Key')
        if not api_key:
            return Response({'error': 'API-Key header is required.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            device = Device.objects.get(api_key=api_key)
            device.last_seen = timezone.now() # Update Heartbeat
            device.save()
        except Device.DoesNotExist:
            return Response({'error': 'Invalid API-Key.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # 2. Find Active Session
        try:
            active_session = Session.objects.get(device=device, is_active=True)
        except Session.DoesNotExist:
            return Response({'error': 'No active session.'}, status=status.HTTP_403_FORBIDDEN)
        except Session.MultipleObjectsReturned:
            active_session = Session.objects.filter(device=device, is_active=True).last()

        # 3. Save the Log
        serializer = FocusLogSerializer(data=request.data)
        if serializer.is_valid():
            new_log = serializer.save(session=active_session)
            
            # --- (A) AUTO-END LOGIC (30 Mins No Face) ---
            if new_log.status == 'NO FACE':
                # Calculate time 30 minutes ago
                time_threshold = timezone.now() - timedelta(minutes=30)
                
                # Only check if session is actually older than 30 mins
                if active_session.start_time < time_threshold:
                    
                    # Check: Has there been ANY 'FOCUSED', 'DISTRACTED', or 'DROWSY' log 
                    # in the last 30 minutes?
                    has_recent_activity = FocusLog.objects.filter(
                        session=active_session,
                        timestamp__gte=time_threshold
                    ).exclude(status='NO FACE').exists()
                    
                    # If NO activity found (meaning 100% NO FACE for 30 mins)
                    if not has_recent_activity:
                        active_session.is_active = False
                        active_session.end_time = timezone.now()
                        active_session.save()
                        print(f"AUTO-END: Session {active_session.id} closed due to 30 mins of inactivity.")
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required
def chat_api_view(request):
    """
    Role-Aware AI Chatbot (Google Gemini).
    Now serves responses in UK English.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            
            if not settings.GEMINI_API_KEY:
                return JsonResponse({'response': "Error: AI Key not configured."}, status=200)

            # --- 1. DEFINE STATIC KNOWLEDGE ---
            faq_knowledge = """
            OFFICIAL KNOWLEDGE BASE:
            - Video Privacy: No video is recorded or stored. Processing is local (Edge AI).
            - Wellness AI: Suggests breaks based on data; does not police work.
            - Data Deletion: Contact admin to wipe data.
            """

            # --- 2. BUILD DYNAMIC CONTEXT ---
            
            if request.user.is_staff:
                # === TEACHER MODE ===
                # A. Define the time window (Last 30 mins)
                time_window = timezone.now() - timedelta(minutes=30)
                
                # B. Find logs for currently active sessions
                active_sessions = Session.objects.filter(is_active=True)
                active_logs = FocusLog.objects.filter(
                    session__in=active_sessions,
                    timestamp__gte=time_window
                )
                
                # C. Calculate Class Percentages
                total_class = active_logs.count()
                
                if total_class > 0:
                    distracted_count = active_logs.filter(status='DISTRACTED').count()
                    drowsy_count = active_logs.filter(status='DROWSY').count()
                    focused_count = active_logs.filter(status='FOCUSED').count()
                    
                    # Calculate percentages
                    distracted_pct = int((distracted_count / total_class) * 100)
                    drowsy_pct = int((drowsy_count / total_class) * 100)
                    focused_pct = int((focused_count / total_class) * 100)
                    
                    context_str = f"LIVE CLASS STATUS: {focused_pct}% Focused, {distracted_pct}% Distracted, {drowsy_pct}% Drowsy."
                else:
                    context_str = "Class is currently inactive."

                # D. Build Teacher Prompt (UK English)
                system_instruction = (
                    "You are an expert Pedagogical Assistant for a teacher. "
                    "Analyze the class statistics below. "
                    "CRITICAL: Use British English spelling and terminology (e.g. 'Maths', 'Module', 'Programme'). " 
                    "Keep advice professional, actionable, and concise (under 50 words)."
                    f"\n\n{faq_knowledge}\n\n{context_str}"
                )

            else:
                # === STUDENT MODE ===
                # A. Get today's logs for this specific user
                today_logs = FocusLog.objects.filter(
                    session__user=request.user,
                    timestamp__date=timezone.now().date()
                )
                total = today_logs.count()
                
                stats_str = "No data yet."
                if total > 0:
                    focused = today_logs.filter(status='FOCUSED').count()
                    pct = int((focused / total) * 100)
                    stats_str = f"Focus Score: {pct}%."

                # B. Build Student Prompt (UK English)
                system_instruction = (
                    "You are a supportive Wellness Coach for a student. "
                    "Use their recent data to give specific advice. "
                    "CRITICAL: Use British English spelling and terminology (e.g. 'minimise', 'colour', 'wellbeing'). "
                    "If they were recently 'Drowsy', suggest a specific break (water, stretch). "
                    "Never be judgmental."
                    f"\n\n{faq_knowledge}\n\nUSER DATA: {stats_str}"
                )

            # --- 3. CALL AI ---
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            full_prompt = f"{system_instruction}\n\nUser Question: {user_message}"
            response = model.generate_content(full_prompt)
            
            return JsonResponse({'response': response.text})

        except Exception as e:
            print(f"AI Error: {e}")
            return JsonResponse({'response': "I'm analysing the data but hit a snag. Ask me again in a moment!"}, status=200)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

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
    Allows a user to correct a log entry.
    Example: User was reading a book (looking down), AI thought they were 'Drowsy'.
    User clicks 'Correct', status changes to 'FOCUSED'.
    """
    try:
        log_to_correct = get_object_or_404(FocusLog, id=log_id)

        # Security Check: Ensure the log belongs to the current user
        if log_to_correct.session.user != request.user:
            messages.error(request, "You do not have permission to modify this log.")
            return redirect('dashboard')

        # Logic: If 'Drowsy' or 'Distracted', flip it to 'Focused'
        original_status = log_to_correct.get_status_display()
        log_to_correct.status = 'FOCUSED'
        
        #  Flag to indicate manual correction
        log_to_correct.manual_correction = True
        
        log_to_correct.save()
        
        messages.success(request, f"Log updated: '{original_status}' changed to 'Focused'.")
        
    except Exception as e:
        messages.error(request, f"Error correcting log: {e}")

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

logger = logging.getLogger(__name__)

# focus_tracker/views.py

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()
                
                # Ensure profile exists
                if not hasattr(user, 'profile'):
                    Profile.objects.create(user=user)

                # Auto-approve consent (since they checked the boxes)
                user.profile.consent_agreed = True
                
                # Handle Image Upload
                image_file = request.FILES.get('profile_picture')
                if image_file:
                    saved_name = handle_profile_picture_upload(image_file)
                    if saved_name:
                        user.profile.profile_picture.name = saved_name
                
                user.profile.save()
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')

                messages.success(request, f"Account created! Welcome, {user.first_name}.")
                return redirect('dashboard')
                
            except Exception as e:
                logger.error(f"Registration Error: {e}")
                messages.error(request, "System error. Please try again.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()
        
    return render(request, 'register.html', {'form': form})

# Simplified Privacy View (Read Only)
def privacy_view(request):
    return render(request, 'privacy.html')

@login_required
def profile_view(request):
    try:
        profile = request.user.profile
    except:
        from .models import Profile 
        profile = Profile.objects.create(user=request.user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_obj = profile_form.save(commit=False)
            image_file = request.FILES.get('profile_picture')
            image_file = request.FILES.get('profile_picture')
            if image_file:
                saved_file_name = handle_profile_picture_upload(image_file)
                
                if saved_file_name:
                    profile_obj.profile_picture.name = saved_file_name
            
            profile_obj.save()
            
            # Now save the object with the correct image link
            profile_obj.save() 
            
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)

    context = {'user_form': user_form, 'profile_form': profile_form}
    return render(request, 'profile.html', context)

def home_view(request):
    return render(request, 'home.html')

def about_view(request):
    return render(request, 'about.html')

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        
        # 1. Check if the form is valid
        if form.is_valid():
            # --- SUCCESS LOGIC ---
            
            # Extract data
            name = form.cleaned_data['name']
            user_email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message_content = form.cleaned_data['message']

            # Find the Admin (Superuser) to send the email TO
            admin_user = User.objects.filter(is_superuser=True).first()
            
            if admin_user and admin_user.email:
                recipient_email = admin_user.email
                print(f"DEBUG: Found Admin User: {admin_user.username}, Email: {recipient_email}")
            else:
                recipient_email = settings.DEFAULT_FROM_EMAIL
                print(f"DEBUG: No Admin email found. Using fallback: {recipient_email}")

            # Prepare the Email
            email_subject = f"CloudFocus Enquiry: {subject}"
            email_body = f"Message from: {name}\nUser Email: {user_email}\n\nMessage:\n{message_content}"

            # Send the Email
            try:
                email = EmailMessage(
                    subject=email_subject,
                    body=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient_email],
                    reply_to=[user_email],
                )
                email.send(fail_silently=False)
                
                print(f"DEBUG: Email successfully sent to {recipient_email}")
                messages.success(request, 'Your message has been sent successfully!')
                return redirect('contact')
                
            except Exception as e:
                print(f"DEBUG: Error sending email: {e}")
                messages.error(request, f"Error sending email: {e}")

        else:
            # --- FAILURE LOGIC (Validation Errors) ---
            print("❌ FORM IS INVALID!")
            print(form.errors) # <--- Check your terminal for this!
            messages.error(request, "Please correct the errors below.")
                
    else:
        form = ContactForm()
        
    return render(request, 'contact.html', {'form': form})


def privacy_view(request):
    """
    Combined Privacy Page.
    - Public: Anyone can read the text.
    - Logged In: Users can submit the Consent Form.
    """
    
    # 1. Handle Form Submission (POST)
    if request.method == 'POST':
        # SECURITY FIX: Prevent anonymous users from submitting
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to save your consent.")
            return redirect('login')

        read_checked = request.POST.get('check_read')
        consent_checked = request.POST.get('check_consent')

        if read_checked and consent_checked:
            try:
                profile = request.user.profile
            except:
                # Create profile if it doesn't exist for the logged-in user
                from .models import Profile
                profile = Profile.objects.create(user=request.user)

            profile.consent_agreed = True
            profile.save()
            
            messages.success(request, "Thank you! You now have full access to CloudFocus.")
            return redirect('dashboard')
        else:
            messages.error(request, "You must agree to all terms to proceed.")

    # 2. Determine if we should show the form (GET)
    show_form = False
    if request.user.is_authenticated:
        try:
            # Show form only if they haven't agreed yet
            if not request.user.profile.consent_agreed:
                show_form = True
        except:
            # If profile is missing, they need to agree/setup
            show_form = True

    return render(request, 'privacy.html', {'show_form': show_form})