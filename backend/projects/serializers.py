from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Customer, Project, ProjectMember

User = get_user_model()


# ─── Customer (legacy — kept for other parts of the system) ───────────────────

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Customer
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ─── Customer dropdown ────────────────────────────────────────────────────────
# Now returns CustomUser records filtered to customer_admin / customer_user.
# Shape: { id, name } — "name" is company if set, otherwise full_name.
# The frontend <select> sends user.id as the project.customer FK value.

class CustomerDropdownSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        return obj.company.strip() if obj.company.strip() else obj.full_name

    class Meta:
        model  = User
        fields = ['id', 'name']


# ─── User dropdown (for assigning team members) ───────────────────────────────

class UserDropdownSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return name or obj.email

    class Meta:
        model  = User
        fields = ['id', 'email', 'full_name', 'role']


# ─── Project Member ───────────────────────────────────────────────────────────

class ProjectMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name  = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model  = ProjectMember
        fields = ['id', 'user', 'user_email', 'user_name', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


# ─── Project — write payload for member assignment ────────────────────────────

class MemberInputSerializer(serializers.Serializer):
    """Used inside ProjectCreateSerializer to accept member assignments."""
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    role = serializers.ChoiceField(choices=ProjectMember.MemberRole.choices,
                                   default=ProjectMember.MemberRole.CUSTOMER_USER)


# ─── Project List ─────────────────────────────────────────────────────────────

class ProjectListSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    member_count  = serializers.SerializerMethodField()

    class Meta:
        model  = Project
        fields = [
            'id', 'name', 'customer', 'customer_name', 'status', 'progress',
            'robot_model', 'start_date', 'expected_end', 'member_count', 'created_at',
        ]

    def get_customer_name(self, obj):
        if not obj.customer:
            return None
        # Show company name if set, otherwise full name
        return obj.customer.company.strip() if obj.customer.company.strip() else obj.customer.full_name

    def get_member_count(self, obj):
        return obj.members.count()


# ─── Project Detail / Create ──────────────────────────────────────────────────

class ProjectDetailSerializer(serializers.ModelSerializer):
    customer_name  = serializers.SerializerMethodField()
    members        = ProjectMemberSerializer(many=True, read_only=True)
    days_remaining = serializers.SerializerMethodField()

    # Write-only: list of {user, role} objects to assign on create/update
    member_assignments = MemberInputSerializer(many=True, write_only=True, required=False)

    class Meta:
        model  = Project
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_customer_name(self, obj):
        if not obj.customer:
            return None
        return obj.customer.company.strip() if obj.customer.company.strip() else obj.customer.full_name

    def get_days_remaining(self, obj):
        if obj.expected_end:
            from django.utils import timezone
            return (obj.expected_end - timezone.now().date()).days
        return None

    def validate_progress(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError('Progress must be between 0 and 100.')
        return value

    def validate_customer(self, value):
        """Ensure the assigned user actually has a customer role."""
        if value and value.role not in ('customer_admin', 'customer_user'):
            raise serializers.ValidationError(
                'The selected user must have a customer_admin or customer_user role.'
            )
        return value

    def validate(self, attrs):
        # Enforce composite unique: customer + name
        customer = attrs.get('customer', getattr(self.instance, 'customer', None))
        name     = attrs.get('name',     getattr(self.instance, 'name', None))

        qs = Project.objects.filter(customer=customer, name=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {'name': f'A project named "{name}" already exists for this customer.'}
            )
        return attrs

    def create(self, validated_data):
        member_assignments = validated_data.pop('member_assignments', [])
        project = Project.objects.create(**validated_data)
        for entry in member_assignments:
            ProjectMember.objects.get_or_create(
                project=project,
                user=entry['user'],
                defaults={'role': entry['role']},
            )
        return project

    def update(self, instance, validated_data):
        member_assignments = validated_data.pop('member_assignments', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if member_assignments is not None:
            # Replace all members with the new assignment list
            instance.members.all().delete()
            for entry in member_assignments:
                ProjectMember.objects.create(
                    project=instance,
                    user=entry['user'],
                    role=entry['role'],
                )
        return instance


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DashboardSerializer(serializers.ModelSerializer):
    customer_name  = serializers.SerializerMethodField()
    open_tickets   = serializers.SerializerMethodField()
    next_milestone = serializers.SerializerMethodField()

    class Meta:
        model  = Project
        fields = [
            'id', 'name', 'customer_name', 'status', 'progress',
            'robot_model', 'contract_number', 'start_date', 'expected_end',
            'open_tickets', 'next_milestone',
        ]

    def get_customer_name(self, obj):
        if not obj.customer:
            return None
        return obj.customer.company.strip() if obj.customer.company.strip() else obj.customer.full_name

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