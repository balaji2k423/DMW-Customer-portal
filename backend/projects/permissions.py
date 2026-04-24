from rest_framework.permissions import BasePermission
from .models import ProjectMember


class IsProjectMember(BasePermission):
    """Allow access only to users who are members of the project."""
    message = 'You are not a member of this project.'

    def has_object_permission(self, request, view, obj):
        return obj.members.filter(user=request.user).exists()


class IsCustomerAdmin(BasePermission):
    """Allow access only to users with customer_admin role."""
    message = 'Only customer admins can perform this action.'

    def has_permission(self, request, view):
        return request.user.role == 'customer_admin'


class IsProjectManagerOrReadOnly(BasePermission):
    """Project managers can write. Others get read-only."""

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.role == 'project_manager'