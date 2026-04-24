from django.db import models
from django.conf import settings


class Notification(models.Model):

    class Type(models.TextChoices):
        MILESTONE_UPDATED  = 'milestone_updated',  'Milestone Updated'
        MILESTONE_COMPLETED = 'milestone_completed', 'Milestone Completed'
        MILESTONE_DELAYED  = 'milestone_delayed',  'Milestone Delayed'
        DOCUMENT_UPLOADED  = 'document_uploaded',  'Document Uploaded'
        DOCUMENT_UPDATED   = 'document_updated',   'Document Updated'
        TICKET_CREATED     = 'ticket_created',     'Ticket Created'
        TICKET_UPDATED     = 'ticket_updated',     'Ticket Updated'
        TICKET_ASSIGNED    = 'ticket_assigned',    'Ticket Assigned'
        TICKET_RESOLVED    = 'ticket_resolved',    'Ticket Resolved'
        TICKET_COMMENTED   = 'ticket_commented',   'Ticket Commented'
        PROJECT_UPDATED    = 'project_updated',    'Project Updated'
        SIGN_OFF_REQUESTED = 'sign_off_requested', 'Sign Off Requested'
        SIGN_OFF_DONE      = 'sign_off_done',      'Sign Off Done'

    recipient   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    actor       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='triggered_notifications'
    )
    type        = models.CharField(max_length=50, choices=Type.choices)
    title       = models.CharField(max_length=255)
    message     = models.TextField()
    is_read     = models.BooleanField(default=False)
    read_at     = models.DateTimeField(null=True, blank=True)

    # Generic link back to the object that triggered this
    project_id   = models.PositiveIntegerField(null=True, blank=True)
    milestone_id = models.PositiveIntegerField(null=True, blank=True)
    document_id  = models.PositiveIntegerField(null=True, blank=True)
    ticket_id    = models.PositiveIntegerField(null=True, blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.type}] → {self.recipient.email}"

    def mark_read(self):
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class ActivityLog(models.Model):
    """
    Global activity feed for a project.
    Shown in the dashboard recent activity section.
    """

    class Action(models.TextChoices):
        CREATED  = 'created',  'Created'
        UPDATED  = 'updated',  'Updated'
        DELETED  = 'deleted',  'Deleted'
        UPLOADED = 'uploaded', 'Uploaded'
        RESOLVED = 'resolved', 'Resolved'
        SIGNED   = 'signed',   'Signed Off'
        COMMENTED = 'commented', 'Commented'
        ASSIGNED = 'assigned', 'Assigned'

    project     = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='activity_logs',
        null=True, blank=True
    )
    actor       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_logs'
    )
    action      = models.CharField(max_length=20, choices=Action.choices)
    entity_type = models.CharField(max_length=50, help_text='e.g. Ticket, Milestone, Document')
    entity_id   = models.PositiveIntegerField(null=True, blank=True)
    entity_name = models.CharField(max_length=255, blank=True)
    detail      = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.actor} {self.action} {self.entity_type} — {self.entity_name}"