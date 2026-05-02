from django.db import models
from django.conf import settings


class Customer(models.Model):
    """
    Kept for backwards compatibility / other parts of the system.
    No longer used as the FK target for Project.customer.
    """
    name        = models.CharField(max_length=200)
    industry    = models.CharField(max_length=100, blank=True)
    address     = models.TextField(blank=True)
    phone       = models.CharField(max_length=20, blank=True)
    email       = models.EmailField(blank=True)
    website     = models.URLField(blank=True)
    logo        = models.ImageField(upload_to='customer_logos/', blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Project(models.Model):

    class Status(models.TextChoices):
        PLANNING    = 'planning',    'Planning'
        IN_PROGRESS = 'in_progress', 'In Progress'
        ON_HOLD     = 'on_hold',     'On Hold'
        COMPLETED   = 'completed',   'Completed'
        CANCELLED   = 'cancelled',   'Cancelled'

    # FK to CustomUser (customer_admin / customer_user role)
    customer        = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='projects',
                        limit_choices_to={'role__in': ['customer_admin', 'customer_user']},
                      )
    name            = models.CharField(max_length=200)
    description     = models.TextField(blank=True)
    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNING)
    progress        = models.PositiveIntegerField(default=0)
    robot_model     = models.CharField(max_length=100, blank=True)
    robot_serial    = models.CharField(max_length=100, blank=True)
    contract_number = models.CharField(max_length=100, blank=True)
    start_date      = models.DateField(null=True, blank=True)
    expected_end    = models.DateField(null=True, blank=True)
    actual_end      = models.DateField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} — {self.customer.full_name if self.customer else 'No Customer'}"

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'name'],
                name='unique_project_name_per_customer',
            )
        ]


class ProjectMember(models.Model):

    class MemberRole(models.TextChoices):
        CUSTOMER_ADMIN  = 'customer_admin',  'Customer Admin'
        CUSTOMER_USER   = 'customer_user',   'Customer User'
        PROJECT_MANAGER = 'project_manager', 'Project Manager'

    project   = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    user      = models.ForeignKey(
                    settings.AUTH_USER_MODEL,
                    on_delete=models.CASCADE,
                    related_name='project_memberships',
                )
    role      = models.CharField(max_length=20, choices=MemberRole.choices, default=MemberRole.CUSTOMER_USER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')
        ordering        = ['joined_at']

    def __str__(self):
        return f"{self.user.email} on {self.project.name}"