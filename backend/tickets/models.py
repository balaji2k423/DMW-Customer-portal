from django.db import models
from django.conf import settings
from django.utils import timezone


class Ticket(models.Model):

    class Priority(models.TextChoices):
        LOW      = 'low',      'Low'
        MEDIUM   = 'medium',   'Medium'
        HIGH     = 'high',     'High'
        CRITICAL = 'critical', 'Critical'

    class Status(models.TextChoices):
        OPEN        = 'open',        'Open'
        IN_PROGRESS = 'in_progress', 'In Progress'
        ON_HOLD     = 'on_hold',     'On Hold'
        RESOLVED    = 'resolved',    'Resolved'
        CLOSED      = 'closed',      'Closed'

    class Category(models.TextChoices):
        TECHNICAL     = 'technical',     'Technical'
        COMMERCIAL    = 'commercial',    'Commercial'
        INSTALLATION  = 'installation',  'Installation'
        TRAINING      = 'training',      'Training'
        OTHER         = 'other',         'Other'

    # Auto-generated ticket ID e.g. TKT-0001
    ticket_id       = models.CharField(max_length=20, unique=True, editable=False)

    project         = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    raised_by       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='raised_tickets'
    )
    assigned_to     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_tickets'
    )

    subject         = models.CharField(max_length=255)
    description     = models.TextField()
    category        = models.CharField(max_length=20, choices=Category.choices, default=Category.TECHNICAL)
    priority        = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    # SLA tracking
    sla_hours       = models.PositiveIntegerField(default=48, help_text='SLA response time in hours')
    sla_due         = models.DateTimeField(null=True, blank=True)
    sla_breached    = models.BooleanField(default=False)

    resolved_at     = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticket_id} — {self.subject}"

    def save(self, *args, **kwargs):
        # Generate ticket ID on first save
        if not self.ticket_id:
            super().save(*args, **kwargs)
            self.ticket_id = f"TKT-{self.pk:04d}"
            Ticket.objects.filter(pk=self.pk).update(ticket_id=self.ticket_id)
            return

        # Set SLA due date on creation
        if not self.sla_due and self.created_at:
            from datetime import timedelta
            self.sla_due = self.created_at + timedelta(hours=self.sla_hours)

        # Check SLA breach
        if self.sla_due and timezone.now() > self.sla_due:
            if self.status not in ('resolved', 'closed'):
                self.sla_breached = True

        # Set resolved timestamp
        if self.status == 'resolved' and not self.resolved_at:
            self.resolved_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.sla_due and self.status not in ('resolved', 'closed'):
            return timezone.now() > self.sla_due
        return False

    @property
    def time_to_resolve(self):
        """Returns hours taken to resolve, or None if not resolved."""
        if self.resolved_at and self.created_at:
            delta = self.resolved_at - self.created_at
            return round(delta.total_seconds() / 3600, 1)
        return None


class TicketComment(models.Model):
    ticket      = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ticket_comments'
    )
    message     = models.TextField()
    is_internal = models.BooleanField(
        default=False,
        help_text='Internal notes visible only to project managers'
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author} on {self.ticket.ticket_id}"


class TicketAttachment(models.Model):
    ticket      = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ticket_attachments'
    )
    file        = models.FileField(upload_to='ticket_attachments/')
    filename    = models.CharField(max_length=255, blank=True)
    file_size   = models.PositiveBigIntegerField(default=0)
    file_type   = models.CharField(max_length=50, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} on {self.ticket.ticket_id}"

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            name = self.file.name
            self.filename  = name.split('/')[-1]
            self.file_type = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
        super().save(*args, **kwargs)


class TicketStatusHistory(models.Model):
    """Audit trail of every status change on a ticket."""
    ticket      = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    changed_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ticket_status_changes'
    )
    from_status = models.CharField(max_length=20, blank=True)
    to_status   = models.CharField(max_length=20)
    note        = models.TextField(blank=True)
    changed_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.ticket.ticket_id}: {self.from_status} → {self.to_status}"