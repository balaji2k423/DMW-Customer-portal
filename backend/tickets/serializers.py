from rest_framework import serializers
from .models import Ticket, TicketComment, TicketAttachment, TicketStatusHistory


class TicketAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    file_url         = serializers.SerializerMethodField()

    class Meta:
        model  = TicketAttachment
        fields = [
            'id', 'file', 'file_url', 'filename',
            'file_size', 'file_type',
            'uploaded_by', 'uploaded_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'filename', 'file_size', 'file_type', 'uploaded_by', 'created_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class TicketCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    author_role = serializers.CharField(source='author.role', read_only=True)

    class Meta:
        model  = TicketComment
        fields = [
            'id', 'ticket', 'message', 'is_internal',
            'author', 'author_name', 'author_role',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def validate(self, data):
        request = self.context.get('request')
        # Only project managers can post internal notes
        if data.get('is_internal') and request.user.role != 'project_manager':
            raise serializers.ValidationError(
                {'is_internal': 'Only project managers can post internal notes.'}
            )
        return data


class TicketStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.full_name', read_only=True)

    class Meta:
        model  = TicketStatusHistory
        fields = ['id', 'from_status', 'to_status', 'note', 'changed_by_name', 'changed_at']
        read_only_fields = fields


class TicketListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for ticket list view."""
    raised_by_name   = serializers.CharField(source='raised_by.full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    project_name     = serializers.CharField(source='project.name', read_only=True)
    comment_count    = serializers.SerializerMethodField()
    is_overdue       = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Ticket
        fields = [
            'id', 'ticket_id', 'subject', 'category',
            'priority', 'status', 'sla_due', 'sla_breached',
            'is_overdue', 'project', 'project_name',
            'raised_by_name', 'assigned_to_name',
            'comment_count', 'created_at', 'updated_at',
        ]

    def get_comment_count(self, obj):
        return obj.comments.filter(is_internal=False).count()


class TicketDetailSerializer(serializers.ModelSerializer):
    """Full ticket detail with thread, attachments, and history."""
    raised_by_name   = serializers.CharField(source='raised_by.full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    project_name     = serializers.CharField(source='project.name', read_only=True)
    comments         = serializers.SerializerMethodField()
    attachments      = TicketAttachmentSerializer(many=True, read_only=True)
    status_history   = TicketStatusHistorySerializer(many=True, read_only=True)
    is_overdue       = serializers.BooleanField(read_only=True)
    time_to_resolve  = serializers.FloatField(read_only=True)

    class Meta:
        model  = Ticket
        fields = '__all__'
        read_only_fields = [
            'id', 'ticket_id', 'raised_by', 'sla_due',
            'sla_breached', 'resolved_at', 'created_at', 'updated_at',
        ]

    def get_comments(self, obj):
        request = self.context.get('request')
        # Hide internal notes from non-project-managers
        qs = obj.comments.all()
        if request and request.user.role != 'project_manager':
            qs = qs.filter(is_internal=False)
        return TicketCommentSerializer(qs, many=True, context=self.context).data


class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Ticket
        fields = [
            'project', 'subject', 'description',
            'category', 'priority', 'sla_hours',
        ]

    def validate_sla_hours(self, value):
        if value < 1:
            raise serializers.ValidationError('SLA hours must be at least 1.')
        return value


class TicketUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Ticket
        fields = [
            'subject', 'description', 'category',
            'priority', 'status', 'assigned_to',
        ]