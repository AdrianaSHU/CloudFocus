from django.urls import path
from .views import (
    LogFocusView, register_view, home_view, dashboard_view, about_view, contact_view, profile_view
)
from django.contrib.auth import views as auth_views

urlpatterns = [
    # API Endpoint
    path('api/log_focus/', LogFocusView.as_view(), name='api-log-focus'),

    # Web Pages
    path('', home_view, name='home'),
    path('register/', register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('dashboard/', dashboard_view, name='dashboard'),
    path('about/', about_view, name='about'),
    path('contact/', contact_view, name='contact'),
    path('profile/', profile_view, name='profile'),

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
]