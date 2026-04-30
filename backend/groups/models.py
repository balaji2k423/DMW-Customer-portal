from django.db import models
from django.conf import settings


class Group(models.Model):
    """
    A customer group / team that can be assigned to projects.
    Admins create groups and assign users + projects to them.
    """
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_groups',
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class GroupMember(models.Model):
    group     = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='members')
    user      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_memberships',
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')
        ordering        = ['joined_at']

    def __str__(self):
        return f"{self.user.email} in {self.group.name}"


class GroupProject(models.Model):
    """Many-to-many link between a Group and a Project."""
    group      = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='group_projects')
    project    = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='group_assignments',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'project')

    def __str__(self):
        return f"{self.group.name} → {self.project.name}"