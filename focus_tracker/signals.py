from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from .models import Session

@receiver(user_logged_out)
def end_active_session_on_logout(sender, request, user, **kwargs):
    """
    Handles the user_logged_out signal by setting any active sessions 
    for that user to inactive.
    """
    if user is not None:
        # Find the active session(s) for the user who just logged out
        active_sessions = Session.objects.filter(user=user, is_active=True)
        
        # Update the session(s): set is_active to False and record end_time
        if active_sessions.exists():
            active_sessions.update(is_active=False, end_time=timezone.now())
            
        print(f"SESSION ENDED: User {user.username} logged out. {active_sessions.count()} sessions closed.")