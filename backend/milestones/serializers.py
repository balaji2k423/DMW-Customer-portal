from rest_framework import serializers
from .models import Milestone, Deliverable, SignOff, Subtask


# ─── Subtask ──────────────────────────────────────────────────────────────────

class SubtaskSerializer(serializers.ModelSerializer):
    # milestone_id is write-only (set by the view via perform_create)
    milestone_id = serializers.IntegerField(source='milestone.id', read_only=True)

    class Meta:
        model  = Subtask
        fields = [
            'id', 'milestone_id', 'title', 'status',
            'assignee_name', 'due_date', 'order',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'milestone_id', 'created_at', 'updated_at']


# ─── Deliverable ──────────────────────────────────────────────────────────────

class DeliverableSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Deliverable
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ─── Sign-off ─────────────────────────────────────────────────────────────────

class SignOffSerializer(serializers.ModelSerializer):
    signed_by_name = serializers.CharField(source='signed_by.full_name', read_only=True)

    class Meta:
        model  = SignOff
        fields = ['id', 'milestone', 'signed_by', 'signed_by_name', 'signed_at', 'remarks']
        read_only_fields = ['id', 'signed_by', 'signed_at']


# ─── Customer helpers — safe, never crash ─────────────────────────────────────

def _safe_customer_id(obj):
    try:
        customer = getattr(obj.project, 'company', None)
        return customer.id if customer else None
    except Exception:
        return None


def _safe_customer_name(obj):
    try:
        customer = getattr(obj.project, 'company', None)
        if not customer:
            return None
        name = getattr(customer, 'full_name', None)
        if name:
            return name
        get_full = getattr(customer, 'get_full_name', None)
        if callable(get_full):
            name = get_full()
            if name and name.strip():
                return name
        return getattr(customer, 'email', None) or str(customer)
    except Exception:
        return None


# ─── Milestone list (lightweight) ────────────────────────────────────────────

class MilestoneListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for timeline/stepper list view."""
    owner_name        = serializers.CharField(source='owner.full_name', read_only=True)
    deliverable_count = serializers.SerializerMethodField()
    is_signed_off     = serializers.SerializerMethodField()
    is_delayed        = serializers.BooleanField(read_only=True)
    subtasks          = SubtaskSerializer(many=True, read_only=True)

    customer_id   = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model  = Milestone
        fields = [
            'id', 'project', 'title', 'description', 'status',
            'planned_date', 'actual_date', 'order',
            'owner_name', 'deliverable_count',
            'is_signed_off', 'is_delayed', 'created_at',
            'customer_id', 'customer_name',
            'subtasks',
        ]

    def get_deliverable_count(self, obj):
        # Use prefetched queryset — no extra DB hit
        return len(obj.deliverables.all())

    def get_is_signed_off(self, obj):
        # FIX: don't use hasattr(obj, 'sign_off') — it can raise RelatedObjectDoesNotExist
        # Instead rely on the prefetch_related('sign_off') done in the view.
        try:
            return obj.sign_off is not None
        except SignOff.DoesNotExist:
            return False
        except Exception:
            return False

    def get_customer_id(self, obj):
        return _safe_customer_id(obj)

    def get_customer_name(self, obj):
        return _safe_customer_name(obj)


# ─── Milestone detail (full) ──────────────────────────────────────────────────

class MilestoneDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested deliverables, subtasks, and sign-off."""
    deliverables  = DeliverableSerializer(many=True, read_only=True)
    subtasks      = SubtaskSerializer(many=True, read_only=True)
    sign_off      = SignOffSerializer(read_only=True)
    owner_name    = serializers.CharField(source='owner.full_name', read_only=True)
    is_delayed    = serializers.BooleanField(read_only=True)
    is_signed_off = serializers.SerializerMethodField()

    customer_id   = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model  = Milestone
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_signed_off(self, obj):
        try:
            return obj.sign_off is not None
        except SignOff.DoesNotExist:
            return False
        except Exception:
            return False

    def get_customer_id(self, obj):
        return _safe_customer_id(obj)

    def get_customer_name(self, obj):
        return _safe_customer_name(obj)

    def validate(self, data):
        planned = data.get('planned_date', getattr(self.instance, 'planned_date', None))
        actual  = data.get('actual_date',  getattr(self.instance, 'actual_date',  None))
        if actual and planned and actual < planned:
            raise serializers.ValidationError(
                {'actual_date': 'Actual date cannot be before planned date.'}
            )
        return data


# ─── Milestone create / update ────────────────────────────────────────────────

class MilestoneCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Milestone
        fields = [
            'project', 'owner', 'title', 'description',
            'status', 'planned_date', 'actual_date', 'order',
        ]

    def validate(self, data):
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