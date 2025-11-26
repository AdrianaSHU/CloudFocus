from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Device, Session, FocusLog, Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_is_active')
    
    def get_is_active(self, instance):
        return instance.is_active
    get_is_active.boolean = True
    get_is_active.short_description = 'Active'

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'has_seen_security_update')
    # Make the field editable from the admin panel
    list_editable = ('has_seen_security_update',)

# We are creating a custom admin view for the Device model
class DeviceAdmin(admin.ModelAdmin):
    # This will display the API key in the list view (very helpful)
    list_display = ('name', 'api_key', 'device_id', 'last_seen', 'is_active')
    
    # This makes the API key read-only (so you don't accidentally change it)
    readonly_fields = ('api_key', 'device_id')

# We are creating a custom admin view for the Session model
class SessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'start_time', 'end_time', 'is_active')
    list_filter = ('is_active', 'device') # Lets you filter by device

class FocusLogAdmin(admin.ModelAdmin):
    list_display = ('session', 'timestamp', 'status', 'temperature', 'humidity')
    list_filter = ('status', 'session__device')


# --- 3. Register your models ---

# Unregister the default User admin and register a Custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register your other models
admin.site.register(Device, DeviceAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(FocusLog, FocusLogAdmin)
admin.site.register(Profile, ProfileAdmin)