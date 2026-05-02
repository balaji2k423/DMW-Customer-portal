from rest_framework.permissions import BasePermission


class CanSignOff(BasePermission):
    """Only customer admins can sign off milestones."""
    message = 'Only customer admins can sign off milestones.'

    def has_permission(self, request, view):
        return request.user.role in ('customer_admin',)


class IsProjectManagerOrReadOnly(BasePermission):
    """Project managers can write. Customers get read-only."""

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.role == 'project_manager'

class IsAdminOrReadOnly(BasePermission):
    """Only admins can create, update, or delete. Everyone else is read-only."""
    message = 'Only admins can create or modify milestones.'

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.is_authenticated and request.user.role == 'admin'