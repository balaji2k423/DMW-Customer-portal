from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Customer, Project, ProjectMember

# Import Company from its own app (adjust if your app label differs)
from company_master.models import Company

User = get_user_model()


# ─── Customer (legacy — kept for other parts of the system) ───────────────────

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Customer
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ─── Company dropdown ─────────────────────────────────────────────────────────
# Step 1: admin picks a company from the Company master.
# Shape: { id, company_name, city, state }

class CompanyDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Company
        fields = ['id', 'company_name', 'city', 'state']


# ─── Customer-admin dropdown (filtered by company) ───────────────────────────
# Step 2: after picking a company, load its customer_admin users.
# Shape: { id, full_name, email }
# The frontend sends these user ids as member_assignments with role=customer_admin.

class CustomerAdminDropdownSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return name or obj.email

    class Meta:
        model  = User
        fields = ['id', 'email', 'full_name']


# ─── User dropdown (for assigning all team members) ───────────────────────────

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
    company_name    = serializers.SerializerMethodField()
    member_count    = serializers.SerializerMethodField()
    # Convenience: list of customer_admin names shown on the card
    customer_admins = serializers.SerializerMethodField()

    class Meta:
        model  = Project
        fields = [
            'id', 'name', 'company', 'company_name', 'customer_admins',
            'status', 'progress', 'robot_model', 'start_date',
            'expected_end', 'member_count', 'created_at',
        ]

    def get_company_name(self, obj):
        return obj.company.company_name if obj.company else None

    def get_member_count(self, obj):
        return obj.members.count()

    def get_customer_admins(self, obj):
        """Return names of all customer_admin members on this project."""
        admins = obj.members.filter(role=ProjectMember.MemberRole.CUSTOMER_ADMIN).select_related('user')
        result = []
        for m in admins:
            name = f"{m.user.first_name or ''} {m.user.last_name or ''}".strip()
            result.append(name or m.user.email)
        return result


# ─── Project Detail / Create ──────────────────────────────────────────────────

class ProjectDetailSerializer(serializers.ModelSerializer):
    company_name    = serializers.SerializerMethodField()
    members         = ProjectMemberSerializer(many=True, read_only=True)
    days_remaining  = serializers.SerializerMethodField()
    customer_admins = serializers.SerializerMethodField()

    # Write-only: list of {user, role} objects to assign on create/update
    member_assignments = MemberInputSerializer(many=True, write_only=True, required=False)

    class Meta:
        model  = Project
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_company_name(self, obj):
        return obj.company.company_name if obj.company else None

    def get_customer_admins(self, obj):
        admins = obj.members.filter(role=ProjectMember.MemberRole.CUSTOMER_ADMIN).select_related('user')
        result = []
        for m in admins:
            name = f"{m.user.first_name or ''} {m.user.last_name or ''}".strip()
            result.append({'id': m.user.id, 'name': name or m.user.email, 'email': m.user.email})
        return result

    def get_days_remaining(self, obj):
        if obj.expected_end:
            from django.utils import timezone
            return (obj.expected_end - timezone.now().date()).days
        return None

    def validate_progress(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError('Progress must be between 0 and 100.')
        return value

    def validate(self, attrs):
        # Enforce composite unique: company + name
        company = attrs.get('company', getattr(self.instance, 'company', None))
        name    = attrs.get('name',    getattr(self.instance, 'name', None))

        qs = Project.objects.filter(company=company, name=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {'name': f'A project named "{name}" already exists for this company.'}
            )

        # Validate that member_assignments tagged customer_admin belong to the chosen company
        member_assignments = attrs.get('member_assignments', [])
        if company and member_assignments:
            for entry in member_assignments:
                user = entry['user']
                role = entry.get('role', '')
                if role == ProjectMember.MemberRole.CUSTOMER_ADMIN:
                    if str(getattr(user, 'company_id', None)) != str(company.id) and \
                       getattr(user, 'company', None) != company.company_name:
                        raise serializers.ValidationError(
                            {'member_assignments': (
                                f'User {user.email} does not belong to {company.company_name}.'
                            )}
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
    company_name    = serializers.SerializerMethodField()
    customer_admins = serializers.SerializerMethodField()
    open_tickets    = serializers.SerializerMethodField()
    next_milestone  = serializers.SerializerMethodField()

    class Meta:
        model  = Project
        fields = [
            'id', 'name', 'company_name', 'customer_admins', 'status', 'progress',
            'robot_model', 'contract_number', 'start_date', 'expected_end',
            'open_tickets', 'next_milestone',
        ]

    def get_company_name(self, obj):
        return obj.company.company_name if obj.company else None

    def get_customer_admins(self, obj):
        admins = obj.members.filter(role=ProjectMember.MemberRole.CUSTOMER_ADMIN).select_related('user')
        result = []
        for m in admins:
            name = f"{m.user.first_name or ''} {m.user.last_name or ''}".strip()
            result.append(name or m.user.email)
        return result

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
