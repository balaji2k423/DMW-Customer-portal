from rest_framework import serializers
from .models import Milestone, Deliverable, SignOff


class DeliverableSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Deliverable
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SignOffSerializer(serializers.ModelSerializer):
    signed_by_name = serializers.CharField(source='signed_by.full_name', read_only=True)

    class Meta:
        model  = SignOff
        fields = ['id', 'milestone', 'signed_by', 'signed_by_name', 'signed_at', 'remarks']
        read_only_fields = ['id', 'signed_by', 'signed_at']


class MilestoneListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for timeline/stepper list view."""
    owner_name        = serializers.CharField(source='owner.full_name', read_only=True)
    deliverable_count = serializers.SerializerMethodField()
    is_signed_off     = serializers.SerializerMethodField()
    is_delayed        = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Milestone
        fields = [
            'id', 'project', 'title', 'status', 'planned_date',
            'actual_date', 'order', 'owner_name', 'deliverable_count',
            'is_signed_off', 'is_delayed', 'created_at',
        ]

    def get_deliverable_count(self, obj):
        return obj.deliverables.count()

    def get_is_signed_off(self, obj):
        return hasattr(obj, 'sign_off')


class MilestoneDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested deliverables and sign-off."""
    deliverables  = DeliverableSerializer(many=True, read_only=True)
    sign_off      = SignOffSerializer(read_only=True)
    owner_name    = serializers.CharField(source='owner.full_name', read_only=True)
    is_delayed    = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Milestone
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        planned = data.get('planned_date', getattr(self.instance, 'planned_date', None))
        actual  = data.get('actual_date',  getattr(self.instance, 'actual_date',  None))
        if actual and planned and actual < planned:
            raise serializers.ValidationError(
                {'actual_date': 'Actual date cannot be before planned date.'}
            )
        return data


class MilestoneCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Milestone
        fields = [
            'project', 'owner', 'title', 'description',
            'status', 'planned_date', 'actual_date', 'order',
        ]

    def validate(self, data):
        # FIX: surface a clear error when `project` is missing instead of
        # letting the DB constraint bubble up as a cryptic 400.
        if not self.instance and not data.get('project'):
            raise serializers.ValidationError(
                {'project': 'A project is required to create a milestone.'}
            )

        planned = data.get('planned_date', getattr(self.instance, 'planned_date', None))
        actual  = data.get('actual_date',  getattr(self.instance, 'actual_date',  None))
        if actual and planned and actual < planned:
            raise serializers.ValidationError(
                {'actual_date': 'Actual date cannot be before planned date.'}
            )
        return data