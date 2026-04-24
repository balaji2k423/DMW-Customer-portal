from rest_framework import serializers
from .models import Customer, Project, ProjectMember


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Customer
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name  = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model  = ProjectMember
        fields = ['id', 'user', 'user_email', 'user_name', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view."""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    member_count  = serializers.SerializerMethodField()

    class Meta:
        model  = Project
        fields = [
            'id', 'name', 'customer_name', 'status', 'progress',
            'robot_model', 'start_date', 'expected_end', 'member_count',
            'created_at',
        ]

    def get_member_count(self, obj):
        return obj.members.count()


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail/create/update."""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    members       = ProjectMemberSerializer(many=True, read_only=True)
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model  = Project
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_days_remaining(self, obj):
        if obj.expected_end:
            from django.utils import timezone
            delta = obj.expected_end - timezone.now().date()
            return delta.days
        return None

    def validate_progress(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError('Progress must be between 0 and 100.')
        return value


class DashboardSerializer(serializers.ModelSerializer):
    """Minimal data for customer dashboard summary cards."""
    customer_name  = serializers.CharField(source='customer.name', read_only=True)
    open_tickets   = serializers.SerializerMethodField()
    next_milestone = serializers.SerializerMethodField()

    class Meta:
        model  = Project
        fields = [
            'id', 'name', 'customer_name', 'status', 'progress',
            'robot_model', 'contract_number', 'start_date', 'expected_end',
            'open_tickets', 'next_milestone',
        ]

    def get_open_tickets(self, obj):
        return obj.tickets.filter(status__in=['open', 'in_progress']).count()

    def get_next_milestone(self, obj):
        milestone = obj.milestones.filter(
            status__in=['pending', 'in_progress']
        ).order_by('planned_date').first()
        if milestone:
            return {
                'id':           milestone.id,
                'title':        milestone.title,
                'planned_date': milestone.planned_date,
                'status':       milestone.status,
            }
        return None