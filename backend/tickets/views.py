from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from api.throttling import BurstRateThrottle, SustainedRateThrottle, IPRateThrottle
from projects.models import ProjectMember
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


def get_user_project_ids(user):
    if user.role in ('project_manager', 'admin'):  # ← added 'admin'
        return None
    return ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)


def get_ticket_queryset(user):
    project_ids = get_user_project_ids(user)
    qs = Ticket.objects.select_related(
        'project', 'raised_by', 'assigned_to'
    )
    if project_ids is None:
        return qs
    return qs.filter(project_id__in=project_ids)


class TicketListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['status', 'priority', 'category', 'project', 'assigned_to', 'sla_breached']
    search_fields      = ['subject', 'description', 'ticket_id']
    ordering_fields    = ['created_at', 'updated_at', 'priority', 'sla_due']

    def get_queryset(self):
        return get_ticket_queryset(self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TicketCreateSerializer
        return TicketListSerializer

    def perform_create(self, serializer):
        ticket = serializer.save(raised_by=self.request.user)
        # Record initial status in history
        TicketStatusHistory.objects.create(
            ticket      = ticket,
            changed_by  = self.request.user,
            from_status = '',
            to_status   = ticket.status,
            note        = 'Ticket created',
        )


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

        # Record status change in history
        if old_status != new_status:
            TicketStatusHistory.objects.create(
                ticket      = ticket,
                changed_by  = self.request.user,
                from_status = old_status,
                to_status   = new_status,
            )


class TicketStatusChangeView(APIView):
    """
    Dedicated endpoint for status transitions with a note.
    POST { "status": "resolved", "note": "Fixed the issue." }
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    VALID_TRANSITIONS = {
        'customer_admin': ['open', 'closed'],
        'customer_user':  ['open'],
        'project_manager': ['open', 'in_progress', 'on_hold', 'resolved', 'closed'],
    }

    def post(self, request, pk):
        try:
            ticket = get_ticket_queryset(request.user).get(pk=pk)
        except Ticket.DoesNotExist:
            return Response({'error': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        note       = request.data.get('note', '')

        if not new_status:
            return Response({'error': 'status field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        allowed = self.VALID_TRANSITIONS.get(request.user.role, [])
        if new_status not in allowed:
            return Response(
                {'error': f'Your role cannot set status to "{new_status}".'},
                status=status.HTTP_403_FORBIDDEN
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

        return Response(
            TicketDetailSerializer(ticket, context={'request': request}).data
        )


class TicketCommentListCreateView(generics.ListCreateAPIView):
    serializer_class   = TicketCommentSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]

    def get_queryset(self):
        qs = TicketComment.objects.filter(
            ticket_id=self.kwargs['ticket_pk']
        ).select_related('author')
        # Hide internal notes from customers
        if self.request.user.role != 'project_manager':
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
            author=self.request.user
        )


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

        # 20 MB limit for ticket attachments
        if file.size > 20 * 1024 * 1024:
            return Response(
                {'error': 'File size cannot exceed 20 MB.'},
                status=status.HTTP_400_BAD_REQUEST
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
                uploaded_by=request.user
            )
        except TicketAttachment.DoesNotExist:
            return Response({'error': 'Attachment not found.'}, status=status.HTTP_404_NOT_FOUND)

        attachment.file.delete(save=False)
        attachment.delete()
        return Response({'message': 'Attachment deleted.'}, status=status.HTTP_204_NO_CONTENT)


class TicketStatusHistoryView(generics.ListAPIView):
    serializer_class   = TicketStatusHistorySerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_queryset(self):
        return TicketStatusHistory.objects.filter(
            ticket_id=self.kwargs['ticket_pk']
        ).select_related('changed_by')


class TicketSummaryView(APIView):
    """
    Returns ticket summary stats for the dashboard.
    Counts by status and priority for the logged-in user's projects.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request):
        qs = get_ticket_queryset(request.user)

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
            }
        }
        return Response(summary)