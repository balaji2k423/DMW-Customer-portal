from django.contrib import admin
from .models import Customer, Project, ProjectMember


class ProjectMemberInline(admin.TabularInline):
    model           = ProjectMember
    extra           = 1
    fields          = ['user', 'role', 'joined_at']
    readonly_fields = ['joined_at']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ['name', 'industry', 'email', 'phone', 'created_at']
    search_fields = ['name', 'industry', 'email']
    ordering      = ['name']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display    = ['name', 'company', 'status', 'progress', 'robot_model', 'start_date', 'expected_end']
    list_filter     = ['status', 'company']
    search_fields   = ['name', 'robot_model', 'contract_number']
    ordering        = ['-created_at']
    inlines         = [ProjectMemberInline]
    readonly_fields = ['created_at', 'updated_at']
    # Show company first so the admin selects it before adding members
    fieldsets = [
        ('Company & Identity', {
            'fields': ['company', 'name', 'description', 'contract_number'],
        }),
        ('Schedule', {
            'fields': ['start_date', 'expected_end', 'actual_end'],
        }),
        ('Robot Details', {
            'fields': ['robot_model', 'robot_serial'],
        }),
        ('Status', {
            'fields': ['status', 'progress'],
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display  = ['user', 'project', 'role', 'joined_at']
    list_filter   = ['role']
    search_fields = ['user__email', 'project__name']