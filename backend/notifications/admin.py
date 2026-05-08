from django.contrib import admin
from .models import Notification, ActivityLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display    = ['recipient', 'type', 'title', 'is_read', 'created_at']
    list_filter     = ['type', 'is_read']
    search_fields   = ['recipient__email', 'title', 'message']
    readonly_fields = ['recipient', 'actor', 'type', 'title', 'message',
                       'is_read', 'read_at', 'project_id', 'milestone_id',
                       'document_id', 'ticket_id', 'created_at']
    ordering        = ['-created_at']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display    = ['actor', 'action', 'entity_type', 'entity_name', 'project', 'created_at']
    list_filter     = ['action', 'entity_type']
    search_fields   = ['actor__email', 'entity_name', 'detail']
    readonly_fields = ['actor', 'project', 'action', 'entity_type',
                       'entity_id', 'entity_name', 'detail', 'created_at']
    ordering        = ['-created_at']