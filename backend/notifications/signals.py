from django.db.models.signals import post_save
from django.dispatch import receiver
from projects.models import ProjectMember
from milestones.models import Milestone, SignOff
from documents.models import Document
from tickets.models import Ticket, TicketComment
from .models import Notification, ActivityLog


def get_project_members(project, exclude_user=None):
    """Returns all users who are members of a project."""
    qs = ProjectMember.objects.filter(project=project).select_related('user')
    if exclude_user:
        qs = qs.exclude(user=exclude_user)
    return [m.user for m in qs]


def bulk_notify(recipients, actor, notif_type, title, message, **kwargs):
    """Creates Notification rows for a list of recipients."""
    notifications = [
        Notification(
            recipient  = user,
            actor      = actor,
            type       = notif_type,
            title      = title,
            message    = message,
            project_id  = kwargs.get('project_id'),
            milestone_id = kwargs.get('milestone_id'),
            document_id  = kwargs.get('document_id'),
            ticket_id    = kwargs.get('ticket_id'),
        )
        for user in recipients
        if user != actor
    ]
    Notification.objects.bulk_create(notifications)


def log_activity(actor, action, entity_type, entity_name,
                 project=None, entity_id=None, detail=''):
    ActivityLog.objects.create(
        project     = project,
        actor       = actor,
        action      = action,
        entity_type = entity_type,
        entity_id   = entity_id,
        entity_name = entity_name,
        detail      = detail,
    )


# ─── Milestone signals ────────────────────────────────────────────────────────

@receiver(post_save, sender=Milestone)
def milestone_saved(sender, instance, created, **kwargs):
    project    = instance.project
    recipients = get_project_members(project)

    if created:
        bulk_notify(
            recipients   = recipients,
            actor        = None,
            notif_type   = Notification.Type.MILESTONE_UPDATED,
            title        = 'New milestone added',
            message      = f'Milestone "{instance.title}" was added to {project.name}.',
            project_id   = project.id,
            milestone_id = instance.id,
        )
        log_activity(
            actor       = None,
            action      = ActivityLog.Action.CREATED,
            entity_type = 'Milestone',
            entity_name = instance.title,
            project     = project,
            entity_id   = instance.id,
        )
    else:
        if instance.status == Milestone.Status.COMPLETED:
            bulk_notify(
                recipients   = recipients,
                actor        = None,
                notif_type   = Notification.Type.MILESTONE_COMPLETED,
                title        = 'Milestone completed',
                message      = f'Milestone "{instance.title}" has been marked as completed.',
                project_id   = project.id,
                milestone_id = instance.id,
            )
            log_activity(
                actor       = None,
                action      = ActivityLog.Action.UPDATED,
                entity_type = 'Milestone',
                entity_name = instance.title,
                project     = project,
                entity_id   = instance.id,
                detail      = 'Marked as completed',
            )


@receiver(post_save, sender=SignOff)
def signoff_saved(sender, instance, created, **kwargs):
    if not created:
        return
    project    = instance.milestone.project
    recipients = get_project_members(project)

    bulk_notify(
        recipients   = recipients,
        actor        = instance.signed_by,
        notif_type   = Notification.Type.SIGN_OFF_DONE,
        title        = 'Milestone signed off',
        message      = (
            f'{instance.signed_by} signed off milestone '
            f'"{instance.milestone.title}".'
        ),
        project_id   = project.id,
        milestone_id = instance.milestone.id,
    )
    log_activity(
        actor       = instance.signed_by,
        action      = ActivityLog.Action.SIGNED,
        entity_type = 'Milestone',
        entity_name = instance.milestone.title,
        project     = project,
        entity_id   = instance.milestone.id,
    )


# ─── Document signals ─────────────────────────────────────────────────────────

@receiver(post_save, sender=Document)
def document_saved(sender, instance, created, **kwargs):
    project    = instance.project
    recipients = get_project_members(project, exclude_user=instance.uploaded_by)
    notif_type = Notification.Type.DOCUMENT_UPLOADED if created else Notification.Type.DOCUMENT_UPDATED
    action     = ActivityLog.Action.UPLOADED if created else ActivityLog.Action.UPDATED
    verb       = 'uploaded' if created else 'updated'

    bulk_notify(
        recipients  = recipients,
        actor       = instance.uploaded_by,
        notif_type  = notif_type,
        title       = f'Document {verb}',
        message     = (
            f'{instance.uploaded_by} {verb} "{instance.title}" '
            f'({instance.category}) in {project.name}.'
        ),
        project_id  = project.id,
        document_id = instance.id,
    )
    log_activity(
        actor       = instance.uploaded_by,
        action      = action,
        entity_type = 'Document',
        entity_name = instance.title,
        project     = project,
        entity_id   = instance.id,
        detail      = f'Version {instance.version}',
    )


# ─── Ticket signals ───────────────────────────────────────────────────────────

@receiver(post_save, sender=Ticket)
def ticket_saved(sender, instance, created, **kwargs):
    project    = instance.project
    recipients = get_project_members(project, exclude_user=instance.raised_by)

    if created:
        bulk_notify(
            recipients = recipients,
            actor      = instance.raised_by,
            notif_type = Notification.Type.TICKET_CREATED,
            title      = 'New support ticket raised',
            message    = (
                f'{instance.raised_by} raised ticket {instance.ticket_id}: '
                f'"{instance.subject}" [{instance.priority.upper()}].'
            ),
            project_id = project.id,
            ticket_id  = instance.id,
        )
        log_activity(
            actor       = instance.raised_by,
            action      = ActivityLog.Action.CREATED,
            entity_type = 'Ticket',
            entity_name = instance.subject,
            project     = project,
            entity_id   = instance.id,
            detail      = f'{instance.ticket_id} — Priority: {instance.priority}',
        )
    else:
        if instance.status == 'resolved':
            bulk_notify(
                recipients = recipients,
                actor      = instance.assigned_to,
                notif_type = Notification.Type.TICKET_RESOLVED,
                title      = 'Ticket resolved',
                message    = (
                    f'Ticket {instance.ticket_id} "{instance.subject}" '
                    f'has been resolved.'
                ),
                project_id = project.id,
                ticket_id  = instance.id,
            )
            log_activity(
                actor       = instance.assigned_to,
                action      = ActivityLog.Action.RESOLVED,
                entity_type = 'Ticket',
                entity_name = instance.subject,
                project     = project,
                entity_id   = instance.id,
                detail      = instance.ticket_id,
            )

        if instance.assigned_to:
            Notification.objects.create(
                recipient  = instance.assigned_to,
                actor      = None,
                type       = Notification.Type.TICKET_ASSIGNED,
                title      = 'Ticket assigned to you',
                message    = (
                    f'You have been assigned ticket {instance.ticket_id}: '
                    f'"{instance.subject}".'
                ),
                project_id = project.id,
                ticket_id  = instance.id,
            )


@receiver(post_save, sender=TicketComment)
def ticket_comment_saved(sender, instance, created, **kwargs):
    if not created or instance.is_internal:
        return

    ticket     = instance.ticket
    project    = ticket.project
    recipients = get_project_members(project, exclude_user=instance.author)

    bulk_notify(
        recipients = recipients,
        actor      = instance.author,
        notif_type = Notification.Type.TICKET_COMMENTED,
        title      = 'New comment on ticket',
        message    = (
            f'{instance.author} commented on ticket '
            f'{ticket.ticket_id}: "{ticket.subject}".'
        ),
        project_id = project.id,
        ticket_id  = ticket.id,
    )
    log_activity(
        actor       = instance.author,
        action      = ActivityLog.Action.COMMENTED,
        entity_type = 'Ticket',
        entity_name = ticket.subject,
        project     = project,
        entity_id   = ticket.id,
        detail      = instance.message[:100],
    )