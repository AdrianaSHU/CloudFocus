from django.urls import path
from .views import (
    LogFocusView, register_view, home_view, dashboard_view, about_view, contact_view, profile_view, 
    supervisor_dashboard_view, supervisor_user_detail_view, start_session_view, end_session_view, 
    get_live_dashboard_data
)
from django.contrib.auth import views as auth_views

urlpatterns = [
    # API Endpoint
    path('api/log_focus/', LogFocusView.as_view(), name='api-log-focus'),
    path('api/live_data/', get_live_dashboard_data, name='api-live-data'),

    # Web Pages
    path('', home_view, name='home'),
    path('register/', register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('dashboard/', dashboard_view, name='dashboard'),
    path('about/', about_view, name='about'),
    path('contact/', contact_view, name='contact'),
    path('profile/', profile_view, name='profile'),

    path('session/start/<int:device_id>/', start_session_view, name='start_session'),
    path('session/end/', end_session_view, name='end_session'),

    # --- THIS BLOCK IS FOR PASSWORD CHANGE ---
    path('password-change/', 
         auth_views.PasswordChangeView.as_view(
             template_name='change_password.html',
             success_url='/password-change/done/' # Redirect to our success page
         ), 
         name='password_change'),
    path('password-change/done/', 
         auth_views.PasswordChangeDoneView.as_view(
             template_name='change_password_done.html'
         ), 
         name='password_change_done'),

    # --- THIS BLOCK IS FOR PASSWORD RESET ---
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='password_reset.html'
         ), 
         name='password_reset'),
         
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='password_reset_done.html'
         ), 
         name='password_reset_done'),
         
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
         
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='password_reset_complete.html'
         ), 
         name='password_reset_complete'),

    # Supervisor
    path('supervisor/', supervisor_dashboard_view, name='supervisor_dashboard'),
    path('supervisor/user/<int:user_id>/', supervisor_user_detail_view, 
         name='supervisor_user_detail'),
]