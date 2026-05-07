from rest_framework import serializers
from .models import Document, DocumentVersion

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

ALLOWED_EXTENSIONS = [
    'pdf', 'doc', 'docx', 'xls', 'xlsx',
    'dwg', 'dxf', 'png', 'jpg', 'jpeg',
    'zip', 'rar', 'txt', 'csv',
]


def _validate_file(value):
    """Shared file validation: size ≤ 5 MB and allowed extension."""
    if value.size > MAX_UPLOAD_BYTES:
        raise serializers.ValidationError(
            f'File size {value.size / 1024 / 1024:.1f} MB exceeds the 5 MB limit.'
        )
    ext = value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise serializers.ValidationError(
            f'File type ".{ext}" is not allowed. '
            f'Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
        )
    return value


class DocumentVersionSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    file_url         = serializers.SerializerMethodField()

    class Meta:
        model  = DocumentVersion
        fields = [
            'id', 'version', 'file', 'file_url',
            'uploaded_by', 'uploaded_by_name',
            'change_note', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'uploaded_by']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for table/grid view."""
    uploaded_by_name  = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    project_name      = serializers.CharField(source='project.name', read_only=True)
    file_url          = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    version_count     = serializers.SerializerMethodField()

    class Meta:
        model  = Document
        fields = [
            'id', 'title', 'category', 'version', 'status',
            'file_url', 'file_type', 'file_size', 'file_size_display',
            'project', 'project_name',
            'uploaded_by_name', 'download_count',
            'is_public', 'created_at', 'updated_at',
            'version_count',
        ]

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

    def get_file_size_display(self, obj):
        return _fmt_size(obj.file_size)

    def get_version_count(self, obj):
        # Count archived versions (current is not in the versions table)
        return obj.versions.count()


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Full serializer including version history."""
    uploaded_by_name  = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    project_name      = serializers.CharField(source='project.name', read_only=True)
    file_url          = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    versions          = DocumentVersionSerializer(many=True, read_only=True)
    version_count     = serializers.SerializerMethodField()

    class Meta:
        model  = Document
        fields = '__all__'
        read_only_fields = [
            'id', 'uploaded_by', 'file_size',
            'file_type', 'download_count',
            'created_at', 'updated_at',
        ]

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

    def get_file_size_display(self, obj):
        return _fmt_size(obj.file_size)

    def get_version_count(self, obj):
        return obj.versions.count()


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Used for initial upload (POST) and metadata-only updates (PATCH without file)."""

    class Meta:
        model  = Document
        fields = [
            'project', 'title', 'description',
            'category', 'file', 'version',
            'status', 'is_public',
        ]

    def validate_file(self, value):
        return _validate_file(value)


class DocumentVersionUploadSerializer(serializers.ModelSerializer):
    """Upload a new version of an existing document (replaces current, archives old)."""

    class Meta:
        model  = DocumentVersion
        fields = ['file', 'version', 'change_note']

    def validate_file(self, value):
        return _validate_file(value)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 ** 2:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 ** 3:
        return f"{size / (1024 ** 2):.1f} MB"
    return f"{size / (1024 ** 3):.1f} GB"