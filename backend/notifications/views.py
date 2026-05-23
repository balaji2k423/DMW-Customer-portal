# notifications/views.py

from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from api.throttling import BurstRateThrottle, SustainedRateThrottle, IPRateThrottle
from projects.models import ProjectMember
from .models import Notification, ActivityLog
from .serializers import NotificationSerializer, ActivityLogSerializer


class NotificationListView(generics.ListAPIView):
    """Returns paginated notifications for the logged-in user."""
    serializer_class   = NotificationSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['is_read', 'type']
    ordering_fields    = ['created_at']

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('actor')


class NotificationUnreadCountView(APIView):
    """Returns unread notification count for the bell icon."""
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count})


class NotificationMarkReadView(APIView):
    """
    POST { "ids": [1, 2, 3] } — marks specific notifications as read.
    POST { "all": true }      — marks all notifications as read.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def post(self, request):
        mark_all = request.data.get('all', False)
        ids      = request.data.get('ids', [])
        now      = timezone.now()

        if mark_all:
            updated = Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).update(is_read=True, read_at=now)
            return Response({'marked_read': updated})

        if ids:
            updated = Notification.objects.filter(
                recipient=request.user,
                id__in=ids,
                is_read=False
            ).update(is_read=True, read_at=now)
            return Response({'marked_read': updated})

        return Response(
            {'error': 'Provide "ids" list or "all": true.'},
            status=status.HTTP_400_BAD_REQUEST
        )


class NotificationMarkSingleReadView(APIView):
    """PATCH /notifications/<id>/read/ — marks one notification as read."""
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        notification.mark_read()
        return Response(NotificationSerializer(notification).data)


class NotificationDeleteView(APIView):
    """DELETE /notifications/<id>/ — removes a notification."""
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def delete(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ActivityLogListView(generics.ListAPIView):
    """
    Global activity feed.

    FIX: previously project_manager saw ALL activity (same as admin).
    Rule: admin sees all; everyone else sees only their project activity.
    project_manager is a member of specific projects via ProjectMember,
    so they should see only those projects' logs, not the entire system log.
    """
    serializer_class   = ActivityLogSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['action', 'entity_type', 'project']
    ordering_fields    = ['created_at']

    def get_queryset(self):
        user = self.request.user
        # FIX: only admin sees the full unrestricted activity log.
        # project_manager was incorrectly given admin-level access here.
        if user.role == 'admin':
            return ActivityLog.objects.all().select_related('actor', 'project')

        project_ids = ProjectMember.objects.filter(
            user=user
        ).values_list('project_id', flat=True)

        return ActivityLog.objects.filter(
            project_id__in=project_ids
        ).select_related('actor', 'project')


class ProjectActivityLogView(generics.ListAPIView):
    """Activity feed scoped to a single project."""
    serializer_class   = ActivityLogSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['action', 'entity_type']
    ordering_fields    = ['created_at']

    def get_queryset(self):
        project_pk = self.kwargs['project_pk']
        user       = self.request.user

        # FIX: previously only project_manager was given unrestricted access
        # to all project logs; admin was incorrectly excluded and subject to
        # the membership check. Admin should always see all project logs.
        if user.role == 'admin':
            return ActivityLog.objects.filter(
                project_id=project_pk
            ).select_related('actor', 'project')

        is_member = ProjectMember.objects.filter(
            user=user,
            project_id=project_pk
        ).exists()
        if not is_member:
            return ActivityLog.objects.none()

        return ActivityLog.objects.filter(
            project_id=project_pk
        ).select_related('actor', 'project')