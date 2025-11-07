from django.contrib import admin
from .models import Device, Session, FocusLog, Profile


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'has_seen_security_update')
    # Make the field editable from the admin panel
    list_editable = ('has_seen_security_update',)

# We are creating a custom admin view for the Device model
class DeviceAdmin(admin.ModelAdmin):
    # This will display the API key in the list view (very helpful)
    list_display = ('name', 'api_key', 'device_id')
    
    # This makes the API key read-only (so you don't accidentally change it)
    readonly_fields = ('api_key', 'device_id')

# We are creating a custom admin view for the Session model
class SessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'start_time', 'end_time', 'is_active')
    list_filter = ('is_active', 'device') # Lets you filter by device

class FocusLogAdmin(admin.ModelAdmin):
    list_display = ('session', 'timestamp', 'status', 'temperature', 'humidity')
    list_filter = ('status', 'session__device')


# --- Register your models ---
admin.site.register(Device, DeviceAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(FocusLog, FocusLogAdmin)
admin.site.register(Profile, ProfileAdmin)