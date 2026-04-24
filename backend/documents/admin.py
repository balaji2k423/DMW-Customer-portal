from django.contrib import admin
from .models import Document, DocumentVersion


class DocumentVersionInline(admin.TabularInline):
    model           = DocumentVersion
    extra           = 0
    fields          = ['version', 'file', 'uploaded_by', 'change_note', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display    = [
        'title', 'project', 'category', 'version',
        'status', 'file_type', 'file_size', 'download_count', 'created_at'
    ]
    list_filter     = ['category', 'status', 'file_type', 'project']
    search_fields   = ['title', 'description', 'version']
    readonly_fields = ['file_size', 'file_type', 'download_count', 'created_at', 'updated_at']
    ordering        = ['-created_at']
    inlines         = [DocumentVersionInline]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display  = ['document', 'version', 'uploaded_by', 'created_at']
    search_fields = ['document__title', 'version']
    readonly_fields = ['created_at']