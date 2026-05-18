"""
tickets/views.py
"""

from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from api.throttling import BurstRateThrottle, SustainedRateThrottle, IPRateThrottle
from projects.models import Project, ProjectMember
from .models import Ticket, TicketComment, TicketAttachment, TicketStatusHistory
from .serializers import (
    TicketListSerializer,
    TicketDetailSerializer,
    TicketCreateSerializer,
    TicketUpdateSerializer,
    TicketCommentSerializer,
    TicketAttachmentSerializer,
    TicketStatusHistorySerializer,
)

# ── Role sets ──────────────────────────────────────────────────────────────────
CUSTOMER_ROLES = ('customer_admin', 'customer_user')
STAFF_ROLES    = ('project_manager', 'admin')


def get_user_project_ids(user):
    """
    Returns a queryset/list of project IDs visible to the user, or None for admins.

    admin           → None  (sees every project / ticket)
    project_manager → only projects they are a ProjectMember of
    customer_*      → only projects they are a ProjectMember of
    """
    if user.role == 'admin':
        return None  # None == "all projects"

    return ProjectMember.objects.filter(
        user=user
    ).values_list('project_id', flat=True)


def get_ticket_queryset(user):
    project_ids = get_user_project_ids(user)
    qs = Ticket.objects.select_related('project', 'raised_by', 'assigned_to')
    if project_ids is None:
        return qs
    return qs.filter(project_id__in=project_ids)


# ── Customer list (mirrors milestones CustomerListView) ────────────────────────

class TicketCustomerListView(APIView):
    """
    GET /tickets/customers/

    Returns the distinct list of customers (companies) whose projects have
    at least one ticket visible to the requesting user.

    Staff (admin / project_manager) see all customers.
    Customers only see their own company — so the list will contain just
    themselves, which is fine (the frontend can hide the dropdown if len == 1).

    Response shape:
        [{ "id": <int|str>, "name": "<company name>" }, ...]

    We derive the customer from project.company (same pattern as the
    milestones app).  Falls back gracefully if the relation doesn't exist.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request):
        qs = get_ticket_queryset(request.user)

        # Collect distinct project IDs from visible tickets
        project_ids = qs.values_list('project_id', flat=True).distinct()

        # Pull projects and extract their company / customer
        projects = Project.objects.filter(id__in=project_ids).select_related('company')

        seen   = {}   # id → name, deduplication
        result = []

        for project in projects:
            try:
                company = getattr(project, 'company', None)
                if not company:
                    continue

                cid = company.id

                if cid in seen:
                    continue

                # Resolve display name — mirrors _safe_customer_name in milestones
                name = getattr(company, 'full_name', None)
                if not name:
                    get_full = getattr(company, 'get_full_name', None)
                    if callable(get_full):
                        name = get_full()
                if not name or not name.strip():
                    name = getattr(company, 'email', None) or str(company)

                seen[cid] = name
                result.append({'id': cid, 'name': name})

            except Exception:
                continue

        # Stable alphabetical sort
        result.sort(key=lambda x: x['name'].lower())
        return Response(result)


# ── Ticket list / create ───────────────────────────────────────────────────────

class TicketListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['status', 'priority', 'category', 'project', 'assigned_to', 'sla_breached']
    search_fields      = ['subject', 'description', 'ticket_id']
    ordering_fields    = ['created_at', 'updated_at', 'priority', 'sla_due']

    def get_queryset(self):
        qs = get_ticket_queryset(self.request.user)

        # ── Customer filter ──────────────────────────────────────────────────
        # ?customer_id=<id>  — filter tickets whose project belongs to the
        # given company/customer.  Staff-only in practice; customers will only
        # ever see their own tickets anyway.
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            try:
                qs = qs.filter(project__company_id=customer_id)
            except Exception:
                pass  # silently ignore if company FK doesn't exist

        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TicketCreateSerializer
        return TicketListSerializer

    def perform_create(self, serializer):
        user = self.request.user

        if user.role not in CUSTOMER_ROLES:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                "Only customer_admin or customer_user accounts may raise support tickets."
            )

        ticket = serializer.save(raised_by=user)

        TicketStatusHistory.objects.create(
            ticket      = ticket,
            changed_by  = user,
            from_status = '',
            to_status   = ticket.status,
            note        = 'Ticket created',
        )

        self._notify_staff(ticket, user)

    @staticmethod
    def _notify_staff(ticket, raised_by):
        """Send in-app notification to all project managers and admins."""
        try:
            from django.contrib.auth import get_user_model
            from notifications.models import Notification

            User = get_user_model()
            staff = User.objects.filter(role__in=STAFF_ROLES, is_active=True)
            for staff_user in staff:
                Notification.objects.create(
                    recipient  = staff_user,
                    actor      = raised_by,
                    type       = Notification.Type.TICKET_CREATED,
                    title      = f"New ticket from {raised_by.full_name or raised_by.email}",
                    message    = ticket.subject,
                    project_id = ticket.project_id,
                    ticket_id  = ticket.pk,
                )
        except Exception:
            pass  # non-fatal


# ── Ticket detail ──────────────────────────────────────────────────────────────

class TicketDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_queryset(self):
        return get_ticket_queryset(self.request.user)

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return TicketUpdateSerializer
        return TicketDetailSerializer

    def perform_update(self, serializer):
        old_status = self.get_object().status
        ticket     = serializer.save()
        new_status = ticket.status

        if old_status != new_status:
            TicketStatusHistory.objects.create(
                ticket      = ticket,
                changed_by  = self.request.user,
                from_status = old_status,
                to_status   = new_status,
            )


# ── Status change ──────────────────────────────────────────────────────────────

class TicketStatusChangeView(APIView):
    """
    POST { "status": "resolved", "note": "Fixed." }

    Permission matrix
    ─────────────────
    customer_admin  : open, closed
    customer_user   : open
    project_manager : open, in_progress, on_hold, resolved, closed
    admin           : in_progress, on_hold, resolved
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    VALID_TRANSITIONS = {
        'customer_admin':  ['open', 'closed'],
        'customer_user':   ['open'],
        'project_manager': ['open', 'in_progress', 'on_hold', 'resolved', 'closed'],
        'admin':           ['in_progress', 'on_hold', 'resolved'],
    }

    def post(self, request, pk):
        try:
            ticket = get_ticket_queryset(request.user).get(pk=pk)
        except Ticket.DoesNotExist:
            return Response({'error': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        note       = request.data.get('note', '')

        if not new_status:
            return Response(
                {'error': 'status field is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed = self.VALID_TRANSITIONS.get(request.user.role, [])
        if new_status not in allowed:
            return Response(
                {'error': f'Your role ({request.user.role}) cannot set status to "{new_status}".'},
                status=status.HTTP_403_FORBIDDEN,
            )

        old_status    = ticket.status
        ticket.status = new_status
        ticket.save()

        TicketStatusHistory.objects.create(
            ticket      = ticket,
            changed_by  = request.user,
            from_status = old_status,
            to_status   = new_status,
            note        = note,
        )

        if new_status in ('resolved', 'closed') and ticket.raised_by:
            try:
                from notifications.models import Notification
                notif_type = (
                    Notification.Type.TICKET_RESOLVED
                    if new_status == 'resolved'
                    else Notification.Type.TICKET_UPDATED
                )
                Notification.objects.create(
                    recipient  = ticket.raised_by,
                    actor      = request.user,
                    type       = notif_type,
                    title      = f"Ticket {ticket.ticket_id} {new_status}",
                    message    = note or f"Your ticket has been {new_status}.",
                    project_id = ticket.project_id,
                    ticket_id  = ticket.pk,
                )
            except Exception:
                pass

        return Response(
            TicketDetailSerializer(ticket, context={'request': request}).data
        )


# ── Comments ───────────────────────────────────────────────────────────────────

class TicketCommentListCreateView(generics.ListCreateAPIView):
    serializer_class   = TicketCommentSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]

    def get_queryset(self):
        qs = TicketComment.objects.filter(
            ticket_id=self.kwargs['ticket_pk']
        ).select_related('author')
        if self.request.user.role not in STAFF_ROLES:
            qs = qs.filter(is_internal=False)
        return qs

    def perform_create(self, serializer):
        try:
            ticket = get_ticket_queryset(self.request.user).get(pk=self.kwargs['ticket_pk'])
        except Ticket.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Ticket not found.')
        serializer.save(author=self.request.user, ticket=ticket)


class TicketCommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = TicketCommentSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_queryset(self):
        return TicketComment.objects.filter(
            ticket_id=self.kwargs['ticket_pk'],
            author=self.request.user,
        )


# ── Attachments ────────────────────────────────────────────────────────────────

IMAGE_MAX_BYTES = 2  * 1024 * 1024   # 2 MB
VIDEO_MAX_BYTES = 10 * 1024 * 1024   # 10 MB
OTHER_MAX_BYTES = 20 * 1024 * 1024   # 20 MB


class TicketAttachmentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]
    parser_classes     = [MultiPartParser, FormParser]

    def get(self, request, ticket_pk):
        attachments = TicketAttachment.objects.filter(ticket_id=ticket_pk)
        serializer  = TicketAttachmentSerializer(
            attachments, many=True, context={'request': request}
        )
        return Response(serializer.data)

    def post(self, request, ticket_pk):
        try:
            ticket = get_ticket_queryset(request.user).get(pk=ticket_pk)
        except Ticket.DoesNotExist:
            return Response({'error': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)

        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)

        content_type = file.content_type or ''

        if content_type.startswith('image/'):
            if file.size > IMAGE_MAX_BYTES:
                return Response(
                    {'error': f'Image files must be ≤ 2 MB (uploaded: {file.size / 1048576:.1f} MB).'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif content_type.startswith('video/'):
            if file.size > VIDEO_MAX_BYTES:
                return Response(
                    {'error': f'Video files must be ≤ 10 MB (uploaded: {file.size / 1048576:.1f} MB).'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            if file.size > OTHER_MAX_BYTES:
                return Response(
                    {'error': 'File size cannot exceed 20 MB.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        attachment = TicketAttachment.objects.create(
            ticket      = ticket,
            uploaded_by = request.user,
            file        = file,
        )
        serializer = TicketAttachmentSerializer(attachment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TicketAttachmentDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def delete(self, request, ticket_pk, pk):
        try:
            attachment = TicketAttachment.objects.get(
                pk=pk,
                ticket_id=ticket_pk,
                uploaded_by=request.user,
            )
        except TicketAttachment.DoesNotExist:
            return Response({'error': 'Attachment not found.'}, status=status.HTTP_404_NOT_FOUND)

        attachment.file.delete(save=False)
        attachment.delete()
        return Response({'message': 'Attachment deleted.'}, status=status.HTTP_204_NO_CONTENT)


# ── Status history ─────────────────────────────────────────────────────────────

class TicketStatusHistoryView(generics.ListAPIView):
    serializer_class   = TicketStatusHistorySerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_queryset(self):
        return TicketStatusHistory.objects.filter(
            ticket_id=self.kwargs['ticket_pk']
        ).select_related('changed_by')


# ── Summary ────────────────────────────────────────────────────────────────────

class TicketSummaryView(APIView):
    """Returns ticket summary stats for the dashboard."""
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request):
        qs = get_ticket_queryset(request.user)

        # ── Customer filter — keeps summary stats consistent with the list ──
        customer_id = request.query_params.get('customer_id')
        if customer_id:
            try:
                qs = qs.filter(project__company_id=customer_id)
            except Exception:
                pass

        summary = {
            'total':       qs.count(),
            'open':        qs.filter(status='open').count(),
            'in_progress': qs.filter(status='in_progress').count(),
            'on_hold':     qs.filter(status='on_hold').count(),
            'resolved':    qs.filter(status='resolved').count(),
            'closed':      qs.filter(status='closed').count(),
            'overdue':     qs.filter(sla_breached=True).count(),
            'by_priority': {
                'critical': qs.filter(priority='critical').count(),
                'high':     qs.filter(priority='high').count(),
                'medium':   qs.filter(priority='medium').count(),
                'low':      qs.filter(priority='low').count(),
            },
        }
        return Response(summary)