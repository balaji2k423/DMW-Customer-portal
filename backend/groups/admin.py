from django.contrib import admin
from .models import Group, GroupMember, GroupProject


class GroupMemberInline(admin.TabularInline):
    model  = GroupMember
    extra  = 1
    fields = ['user', 'joined_at']
    readonly_fields = ['joined_at']


class GroupProjectInline(admin.TabularInline):
    model  = GroupProject
    extra  = 1
    fields = ['project', 'assigned_at']
    readonly_fields = ['assigned_at']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display  = ['name', 'created_by', 'created_at']
    search_fields = ['name']
    inlines       = [GroupMemberInline, GroupProjectInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display  = ['user', 'group', 'joined_at']
    search_fields = ['user__email', 'group__name']


@admin.register(GroupProject)
class GroupProjectAdmin(admin.ModelAdmin):
    list_display  = ['group', 'project', 'assigned_at']