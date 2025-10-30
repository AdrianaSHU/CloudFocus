from django.urls import path
from .views import LogFocusView, register_view, home_view, dashboard_view

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
]