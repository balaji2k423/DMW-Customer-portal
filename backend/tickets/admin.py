from django.contrib import admin
from .models import Ticket, TicketComment, TicketAttachment, TicketStatusHistory


class TicketCommentInline(admin.TabularInline):
    model           = TicketComment
    extra           = 0
    fields          = ['author', 'message', 'is_internal', 'created_at']
    readonly_fields = ['created_at']


class TicketAttachmentInline(admin.TabularInline):
    model           = TicketAttachment
    extra           = 0
    fields          = ['uploaded_by', 'file', 'filename', 'file_size', 'created_at']
    readonly_fields = ['filename', 'file_size', 'created_at']


class TicketStatusHistoryInline(admin.TabularInline):
    model           = TicketStatusHistory
    extra           = 0
    fields          = ['changed_by', 'from_status', 'to_status', 'note', 'changed_at']
    readonly_fields = ['changed_at']
    can_delete      = False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display    = [
        'ticket_id', 'subject', 'project', 'raised_by',
        'assigned_to', 'priority', 'status',
        'sla_breached', 'created_at'
    ]
    list_filter     = ['status', 'priority', 'category', 'sla_breached']
    search_fields   = ['ticket_id', 'subject', 'description']
    readonly_fields = ['ticket_id', 'sla_due', 'sla_breached', 'resolved_at', 'created_at', 'updated_at']
    ordering        = ['-created_at']
    inlines         = [TicketCommentInline, TicketAttachmentInline, TicketStatusHistoryInline]


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display  = ['ticket', 'author', 'is_internal', 'created_at']
    list_filter   = ['is_internal']
    search_fields = ['ticket__ticket_id', 'message', 'author__email']
    readonly_fields = ['created_at']


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display  = ['filename', 'ticket', 'uploaded_by', 'file_size', 'created_at']
    search_fields = ['filename', 'ticket__ticket_id']
    readonly_fields = ['filename', 'file_size', 'file_type', 'created_at']


@admin.register(TicketStatusHistory)
class TicketStatusHistoryAdmin(admin.ModelAdmin):
    list_display  = ['ticket', 'from_status', 'to_status', 'changed_by', 'changed_at']
    search_fields = ['ticket__ticket_id']
    readonly_fields = ['changed_at']
    can_delete    = False