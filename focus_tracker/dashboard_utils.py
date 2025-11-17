from .models import FocusLog
from django.utils import timezone
from datetime import timedelta, datetime
from collections import Counter
import json

# --- get_date_range_from_request is unchanged ---
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

# --- get_dashboard_data is UPDATED ---
def get_dashboard_data(user, request_get):
    """
    Returns dashboard data for a user, ready for Plotly charts.
    """
    
    start_date, end_date = get_date_range_from_request(request_get)
    
    # We query the logs here
    logs = list(FocusLog.objects.filter(
        session__user=user,
        timestamp__range=(start_date, end_date)
    ).order_by('timestamp')) # Changed to ascending for the log table
    
    # Get the latest log, regardless of date range, for temp/humidity
    latest_log = FocusLog.objects.filter(session__user=user).order_by('-timestamp').first()

    # Percentages
    total_logs = len(logs)
    if total_logs > 0:
        status_counts = Counter([log.status for log in logs])
        focused_percent = (status_counts.get('FOCUSED', 0) / total_logs) * 100
        distracted_percent = (status_counts.get('DISTRACTED', 0) / total_logs) * 100
        drowsy_percent = (status_counts.get('DROWSY', 0) / total_logs) * 100
    else:
        focused_percent = distracted_percent = drowsy_percent = 0

    latest_temp = latest_humidity = None
    if latest_log:
        latest_temp = latest_log.temperature
        latest_humidity = latest_log.humidity

    # --- Prepare history arrays for Plotly ---
    timestamps = [log.timestamp.isoformat() for log in logs]
    
    # This logic creates the stepped chart data
    status_map = {'DROWSY': 0, 'DISTRACTED': 1, 'FOCUSED': 2, 'NO FACE': None}
    chart_data = []
    for log in logs:
        y_val = status_map.get(log.status)
        if y_val is not None:
            chart_data.append({'x': log.timestamp.isoformat(), 'y': y_val})

    return {
        'focused_percent': round(focused_percent, 0),
        'distracted_percent': round(distracted_percent, 0),
        'drowsy_percent': round(drowsy_percent, 0),
        'latest_temp': latest_temp,
        'latest_humidity': latest_humidity,
        
        # We use json.dumps here to make it safe for Plotly
        'chart_data_json': json.dumps(chart_data),
        
        'start_date_str': start_date.strftime('%Y-%m-%d'),
        'end_date_str': end_date.strftime('%Y-%m-%d'),
        'chart_min_date': start_date.isoformat(),
        
        # --- (1) THE ONLY CHANGE IS ADDING THIS LINE ---
        # This passes the full list of log objects to the template
        'logs': logs,
    }