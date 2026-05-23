# projects/permissions.py

from rest_framework.permissions import BasePermission, SAFE_METHODS
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
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'customer_admin'
        )


class IsProjectManagerOrReadOnly(BasePermission):
    """
    LEGACY — kept for non-project endpoints (e.g. Customer records).
    project_manager and admin can write. Others get read-only.
    Do NOT use this on Project or ProjectMember views — use IsAdminOrReadOnly.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ('project_manager', 'admin')
        )


class IsAdminOrReadOnly(BasePermission):
    """
    Only users with role == 'admin' can write (POST / PUT / PATCH / DELETE).
    All authenticated users can read (GET / HEAD / OPTIONS).

    Required on ALL Project and ProjectMember views — no one except admin
    may create, edit, or delete a project or its members.
    """
    message = 'Only admins can perform this action.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )