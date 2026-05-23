# milestones/permissions.py

from rest_framework.permissions import BasePermission, SAFE_METHODS


class CanSignOff(BasePermission):
    """
    FIX: Previously allowed customer_admin to sign off / approve milestones.
    Rule: only admin and project_manager may approve (sign off) a milestone.
    customer_admin must NOT be able to approve milestones.
    """
    message = 'Only project managers and admins can approve milestones.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ('project_manager', 'admin')
        )


class IsProjectManagerOrAdmin(BasePermission):
    """
    project_manager and admin can write (create / edit / delete milestones).
    All authenticated users get read-only (GET / HEAD / OPTIONS).

    Rule: milestones can be created by both admin and project_manager.
    Previously IsProjectManagerOrReadOnly excluded admin from writes,
    and IsAdminOrReadOnly excluded project_manager from writes — both wrong.
    This class correctly allows both roles to write.
    """
    message = 'Only project managers and admins can create or modify milestones.'

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
    Kept for any view that should be admin-write-only.
    Not used on milestone create/edit — use IsProjectManagerOrAdmin there.
    """
    message = 'Only admins can create or modify this resource.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )