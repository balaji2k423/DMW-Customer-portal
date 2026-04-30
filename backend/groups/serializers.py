from rest_framework import serializers
from .models import Group, GroupMember, GroupProject


class GroupMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name  = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model  = GroupMember
        fields = ['id', 'user', 'user_email', 'user_name', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class GroupProjectSerializer(serializers.ModelSerializer):
    project_name   = serializers.CharField(source='project.name', read_only=True)
    customer_name  = serializers.CharField(source='project.customer.name', read_only=True)

    class Meta:
        model  = GroupProject
        fields = ['id', 'project', 'project_name', 'customer_name', 'assigned_at']
        read_only_fields = ['id', 'assigned_at']


class GroupListSerializer(serializers.ModelSerializer):
    member_count  = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model  = Group
        fields = [
            'id', 'name', 'description',
            'member_count', 'project_count',
            'created_by_name', 'created_at',
        ]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_project_count(self, obj):
        return obj.group_projects.count()


class GroupDetailSerializer(serializers.ModelSerializer):
    members       = GroupMemberSerializer(many=True, read_only=True)
    group_projects = GroupProjectSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model  = Group
        fields = [
            'id', 'name', 'description',
            'members', 'group_projects',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class GroupCreateSerializer(serializers.ModelSerializer):
    """Used for creating a group; accepts optional user_ids and project_ids."""
    user_ids    = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list
    )
    project_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, default=list
    )

    class Meta:
        model  = Group
        fields = ['id', 'name', 'description', 'user_ids', 'project_ids']
        read_only_fields = ['id']

    def create(self, validated_data):
        user_ids    = validated_data.pop('user_ids', [])
        project_ids = validated_data.pop('project_ids', [])

        request = self.context.get('request')
        validated_data['created_by'] = request.user if request else None

        group = super().create(validated_data)

        # Bulk-create members
        from accounts.models import CustomUser
        from projects.models import Project
        members = [
            GroupMember(group=group, user_id=uid)
            for uid in user_ids
            if CustomUser.objects.filter(pk=uid).exists()
        ]
        GroupMember.objects.bulk_create(members, ignore_conflicts=True)

        # Bulk-create project assignments
        assignments = [
            GroupProject(group=group, project_id=pid)
            for pid in project_ids
            if Project.objects.filter(pk=pid).exists()
        ]
        GroupProject.objects.bulk_create(assignments, ignore_conflicts=True)

        return group