from .models import FocusLog
from django.utils import timezone
from datetime import timedelta, datetime
from collections import Counter
import json

def get_date_range_from_request(request_get):
    """
    Gets start/end dates from the URL query.
    Defaults to the last 24 hours if no dates are provided.
    """
    # Get dates from URL (e.g., ?start=2025-10-30&end=2025-10-31)
    start_date_str = request_get.get('start', None)
    end_date_str = request_get.get('end', None)

    if start_date_str and end_date_str:
        # If dates are provided, parse them
        try:
            # Add time to the dates to cover the full range
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(
                hour=0, minute=0, second=0, tzinfo=timezone.get_current_timezone()
            )
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(
                hour=23, minute=59, second=59, tzinfo=timezone.get_current_timezone()
            )
            return start_date, end_date
        except ValueError:
            pass # Fallback to default

    # --- DEFAULT: LAST 24 HOURS ---
    # If no dates are provided (or they are invalid), default to last 24 hours
    end_date = timezone.now()
    start_date = end_date - timedelta(hours=24)
    return start_date, end_date

def get_dashboard_data(user, request_get):
    """
    A single, reusable function to get all data for any dashboard.
    Filters by the given user and a dynamic time period.
    """
    
    # 1. Get the start and end dates from the request
    start_date, end_date = get_date_range_from_request(request_get)
    
    # 2. Get all logs for the user within that time period
    logs = list(FocusLog.objects.filter(
        session__user=user,
        timestamp__range=(start_date, end_date) # Use range filter
    ).order_by('timestamp'))
    
    # 3. Get the most recent log (for sensors)
    latest_log = FocusLog.objects.filter(session__user=user).order_by('-timestamp').first()

    # 4. Calculate percentages
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

    # 5. Prepare sensor data
    latest_temp = None
    latest_humidity = None
    if latest_log:
        latest_temp = latest_log.temperature
        latest_humidity = latest_log.humidity

    # 6. Prepare chart data
    status_map = {'FOCUSED': 2, 'DISTRACTED': 1, 'DROWSY': 0}
    chart_data = [
        {'x': log.timestamp.isoformat(), 'y': status_map.get(log.status, 1)} 
        for log in logs
    ]

    # 7. Return everything in a clean dictionary
    return {
        'focused_percent': round(focused_percent, 0),
        'distracted_percent': round(distracted_percent, 0),
        'drowsy_percent': round(drowsy_percent, 0),
        'latest_temp': latest_temp,
        'latest_humidity': latest_humidity,
        'chart_data_json': json.dumps(chart_data),
        'start_date_str': start_date.strftime('%Y-%m-%d'), # For pre-filling the form
        'end_date_str': end_date.strftime('%Y-%m-%d'),   # For pre-filling the form
        'chart_min_date': start_date.isoformat(),
    }