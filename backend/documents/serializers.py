from rest_framework import serializers
from .models import Document, DocumentVersion


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
    """Lightweight serializer for document library table view."""
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    project_name     = serializers.CharField(source='project.name', read_only=True)
    file_url         = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()

    class Meta:
        model  = Document
        fields = [
            'id', 'title', 'category', 'version', 'status',
            'file_url', 'file_type', 'file_size', 'file_size_display',
            'project', 'project_name',
            'uploaded_by_name', 'download_count',
            'is_public', 'created_at', 'updated_at',
        ]

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

    def get_file_size_display(self, obj):
        size = obj.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 ** 3:
            return f"{size / (1024 ** 2):.1f} MB"
        return f"{size / (1024 ** 3):.1f} GB"


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Full serializer with version history."""
    uploaded_by_name  = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    project_name      = serializers.CharField(source='project.name', read_only=True)
    file_url          = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    versions          = DocumentVersionSerializer(many=True, read_only=True)

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
        size = obj.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 ** 3:
            return f"{size / (1024 ** 2):.1f} MB"
        return f"{size / (1024 ** 3):.1f} GB"


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Used for create and version-bump updates."""
    class Meta:
        model  = Document
        fields = [
            'project', 'title', 'description',
            'category', 'file', 'version',
            'status', 'is_public',
        ]

    def validate_file(self, value):
        max_size = 50 * 1024 * 1024  # 50 MB
        if value.size > max_size:
            raise serializers.ValidationError('File size cannot exceed 50 MB.')
        allowed_types = [
            'pdf', 'doc', 'docx', 'xls', 'xlsx',
            'dwg', 'dxf', 'png', 'jpg', 'jpeg',
            'zip', 'rar', 'txt', 'csv',
        ]
        ext = value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
        if ext not in allowed_types:
            raise serializers.ValidationError(
                f'File type ".{ext}" is not allowed. '
                f'Allowed types: {", ".join(allowed_types)}'
            )
        return value


class DocumentVersionUploadSerializer(serializers.ModelSerializer):
    """Upload a new version of an existing document."""
    class Meta:
        model  = DocumentVersion
        fields = ['file', 'version', 'change_note']

    def validate_file(self, value):
        max_size = 50 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError('File size cannot exceed 50 MB.')
        return value