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

    # These methods ensure ONLY Superusers can see/edit Users in the Admin Panel.
    # Supervisors (Staff) will NOT see the "Users" table at all.

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    # ----------------------------

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'has_seen_security_update')
    list_editable = ('has_seen_security_update',)

    # Hide Profiles from non-superusers too (optional, but recommended for privacy)
    def has_module_permission(self, request):
        return request.user.is_superuser

class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'api_key', 'device_id', 'last_seen', 'is_active')
    readonly_fields = ('api_key', 'device_id')

class SessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'start_time', 'end_time', 'is_active')
    list_filter = ('is_active', 'device')

class FocusLogAdmin(admin.ModelAdmin):
    list_display = ('session', 'timestamp', 'status', 'temperature', 'humidity')
    list_filter = ('status', 'session__device')


# --- Register your models ---
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

admin.site.register(Device, DeviceAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(FocusLog, FocusLogAdmin)
admin.site.register(Profile, ProfileAdmin)