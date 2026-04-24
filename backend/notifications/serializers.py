from rest_framework import serializers
from .models import Notification, ActivityLog


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model  = Notification
        fields = [
            'id', 'type', 'title', 'message',
            'is_read', 'read_at', 'actor_name',
            'project_id', 'milestone_id',
            'document_id', 'ticket_id',
            'created_at',
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.full_name
        return 'System'


class ActivityLogSerializer(serializers.ModelSerializer):
    actor_name   = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()

    class Meta:
        model  = ActivityLog
        fields = [
            'id', 'action', 'entity_type', 'entity_id',
            'entity_name', 'detail', 'actor_name',
            'project_name', 'created_at',
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.full_name
        return 'System'

    def get_project_name(self, obj):
        if obj.project:
            return obj.project.name
        return None