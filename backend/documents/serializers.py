from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Document, DocumentVersion

User = get_user_model()


# ─── Document Version ─────────────────────────────────────────────────────────

class DocumentVersionSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    def get_uploaded_by_name(self, obj):
        if not obj.uploaded_by:
            return "Unknown"
        name = f"{obj.uploaded_by.first_name or ''} {obj.uploaded_by.last_name or ''}".strip()
        return name or obj.uploaded_by.email

    class Meta:
        model  = DocumentVersion
        fields = ['id', 'version', 'file', 'uploaded_by_name', 'change_note', 'created_at']
        read_only_fields = ['id', 'created_at']


# ─── Document List ────────────────────────────────────────────────────────────

class DocumentListSerializer(serializers.ModelSerializer):
    uploaded_by_name  = serializers.SerializerMethodField()
    project_name      = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    version_count     = serializers.SerializerMethodField()

    def get_uploaded_by_name(self, obj):
        if not obj.uploaded_by:
            return "Unknown"
        name = f"{obj.uploaded_by.first_name or ''} {obj.uploaded_by.last_name or ''}".strip()
        return name or obj.uploaded_by.email

    def get_project_name(self, obj):
        return obj.project.name if obj.project else None

    def get_file_size_display(self, obj):
        size = obj.file_size or 0
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / 1024 / 1024:.2f} MB"

    def get_version_count(self, obj):
        return obj.versions.count()

    class Meta:
        model  = Document
        fields = [
            'id', 'title', 'description', 'category', 'version', 'status',
            'file', 'file_type', 'file_size', 'file_size_display',
            'project', 'project_name', 'uploaded_by_name',
            'download_count', 'is_public', 'created_at', 'updated_at',
            'version_count',
        ]


# ─── Document Detail ──────────────────────────────────────────────────────────

class DocumentDetailSerializer(serializers.ModelSerializer):
    uploaded_by_name  = serializers.SerializerMethodField()
    project_name      = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    version_count     = serializers.SerializerMethodField()
    versions          = DocumentVersionSerializer(many=True, read_only=True)

    def get_uploaded_by_name(self, obj):
        if not obj.uploaded_by:
            return "Unknown"
        name = f"{obj.uploaded_by.first_name or ''} {obj.uploaded_by.last_name or ''}".strip()
        return name or obj.uploaded_by.email

    def get_project_name(self, obj):
        return obj.project.name if obj.project else None

    def get_file_size_display(self, obj):
        size = obj.file_size or 0
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / 1024 / 1024:.2f} MB"

    def get_version_count(self, obj):
        return obj.versions.count()

    class Meta:
        model  = Document
        fields = [
            'id', 'title', 'description', 'category', 'version', 'status',
            'file', 'file_type', 'file_size', 'file_size_display',
            'project', 'project_name', 'uploaded_by_name',
            'download_count', 'is_public', 'created_at', 'updated_at',
            'version_count', 'versions',
        ]
        read_only_fields = ['id', 'file_size', 'file_type', 'download_count', 'created_at', 'updated_at']


# ─── Document Upload (write) ──────────────────────────────────────────────────

class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Document
        fields = ['project', 'title', 'description', 'category', 'file', 'version', 'status', 'is_public']

    def validate_file(self, value):
        max_bytes = 5 * 1024 * 1024  # 5 MB
        if value.size > max_bytes:
            raise serializers.ValidationError("File size must not exceed 5 MB.")
        return value


# ─── Version Upload (write) ───────────────────────────────────────────────────

class DocumentVersionUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DocumentVersion
        fields = ['file', 'version', 'change_note']

    def validate_file(self, value):
        max_bytes = 5 * 1024 * 1024  # 5 MB
        if value.size > max_bytes:
            raise serializers.ValidationError("File size must not exceed 5 MB.")
        return value