from django.urls import path
from .views import LogFocusView 
# We will import more views here later

urlpatterns = [
    # API Endpoint
    path('api/log_focus/', LogFocusView.as_view(), name='api-log-focus'),

    # Web/Dashboard URLs will be added here
]