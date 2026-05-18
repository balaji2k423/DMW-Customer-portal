from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, GuestPermission

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display  = ['email', 'first_name', 'last_name', 'role', 'company', 'is_active']
    list_filter   = ['role', 'is_active', 'mfa_enabled']
    search_fields = ['email', 'first_name', 'last_name', 'company']
    ordering      = ['-date_joined']

    fieldsets = (
        (None,          {'fields': ('email', 'password')}),
        ('Personal',    {'fields': ('first_name', 'last_name', 'phone', 'company')}),
        ('Role',        {'fields': ('role', 'mfa_enabled')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')}),
    )
    add_fieldsets = (
        (None, {'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role')}),
    )


@admin.register(GuestPermission)
class GuestPermissionAdmin(admin.ModelAdmin):
    list_display  = ['guest', 'module', 'project_id', 'customer_id']
    list_filter   = ['module']
    search_fields = ['guest__email', 'guest__first_name', 'guest__last_name']
    autocomplete_fields = ['guest']