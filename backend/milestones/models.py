from django.db import models
from django.conf import settings


class Milestone(models.Model):

    class Status(models.TextChoices):
        PENDING     = 'pending',     'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED   = 'completed',   'Completed'
        DELAYED     = 'delayed',     'Delayed'
        CANCELLED   = 'cancelled',   'Cancelled'

    project      = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='milestones'
    )
    owner        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='owned_milestones'
    )
    title        = models.CharField(max_length=200)
    description  = models.TextField(blank=True)
    status       = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    planned_date = models.DateField()
    actual_date  = models.DateField(null=True, blank=True)
    order        = models.PositiveIntegerField(default=0, help_text='Display order in timeline')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'planned_date']

    def __str__(self):
        return f"{self.title} — {self.project.name}"

    @property
    def is_delayed(self):
        from django.utils import timezone
        if self.status not in ('completed', 'cancelled') and self.planned_date:
            return self.planned_date < timezone.now().date()
        return False


class Deliverable(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Pending'
        SUBMITTED  = 'submitted',  'Submitted'
        APPROVED   = 'approved',   'Approved'
        REJECTED   = 'rejected',   'Rejected'

    milestone   = models.ForeignKey(
        Milestone,
        on_delete=models.CASCADE,
        related_name='deliverables'
    )
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    file        = models.FileField(upload_to='deliverables/', null=True, blank=True)
    due_date    = models.DateField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'created_at']

    def __str__(self):
        return f"{self.title} ({self.milestone.title})"


class Subtask(models.Model):
    """
    Actionable checklist items nested under a Milestone.
    The frontend tracks todo → in_progress → done → approved states.
    """

    class Status(models.TextChoices):
        TODO        = 'todo',        'To Do'
        IN_PROGRESS = 'in_progress', 'In Progress'
        DONE        = 'done',        'Done'
        APPROVED    = 'approved',    'Approved'

    milestone     = models.ForeignKey(
        Milestone,
        on_delete=models.CASCADE,
        related_name='subtasks'
    )
    title         = models.CharField(max_length=300)
    status        = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    assignee_name = models.CharField(max_length=150, blank=True)
    due_date      = models.DateField(null=True, blank=True)
    order         = models.PositiveIntegerField(default=0, help_text='Display order within milestone')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}] — {self.milestone.title}"


class SignOff(models.Model):
    """Customer sign-off record per milestone."""
    milestone  = models.OneToOneField(
        Milestone,
        on_delete=models.CASCADE,
        related_name='sign_off'
    )
    signed_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sign_offs'
    )
    signed_at  = models.DateTimeField(auto_now_add=True)
    remarks    = models.TextField(blank=True)

    def __str__(self):
        return f"Sign-off: {self.milestone.title} by {self.signed_by}"