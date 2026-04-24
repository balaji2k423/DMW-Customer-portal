from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from api.throttling import BurstRateThrottle, SustainedRateThrottle, IPRateThrottle
from .models import Milestone, Deliverable, SignOff
from .serializers import (
    MilestoneListSerializer,
    MilestoneDetailSerializer,
    MilestoneCreateUpdateSerializer,
    DeliverableSerializer,
    SignOffSerializer,
)
from .permissions import CanSignOff, IsProjectManagerOrReadOnly


class MilestoneListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields   = ['status', 'project']
    search_fields      = ['title', 'description']
    ordering_fields    = ['planned_date', 'order', 'created_at']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'project_manager':
            return Milestone.objects.all().select_related('owner', 'project')
        from projects.models import ProjectMember
        project_ids = ProjectMember.objects.filter(
            user=user
        ).values_list('project_id', flat=True)
        return Milestone.objects.filter(
            project_id__in=project_ids
        ).select_related('owner', 'project')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MilestoneCreateUpdateSerializer
        return MilestoneListSerializer


class MilestoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'project_manager':
            return Milestone.objects.all().select_related('owner', 'project')
        from projects.models import ProjectMember
        project_ids = ProjectMember.objects.filter(
            user=user
        ).values_list('project_id', flat=True)
        return Milestone.objects.filter(
            project_id__in=project_ids
        ).select_related('owner', 'project')

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return MilestoneCreateUpdateSerializer
        return MilestoneDetailSerializer


class MilestoneSignOffView(APIView):
    """
    POST — Customer admin signs off a milestone.
    DELETE — Remove an existing sign-off (project manager only).
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_milestone(self, pk):
        try:
            return Milestone.objects.get(pk=pk)
        except Milestone.DoesNotExist:
            return None

    def post(self, request, pk):
        if request.user.role not in ('customer_admin',):
            return Response(
                {'error': 'Only customer admins can sign off milestones.'},
                status=status.HTTP_403_FORBIDDEN
            )
        milestone = self.get_milestone(pk)
        if not milestone:
            return Response({'error': 'Milestone not found.'}, status=status.HTTP_404_NOT_FOUND)

        if hasattr(milestone, 'sign_off'):
            return Response(
                {'error': 'This milestone has already been signed off.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        sign_off = SignOff.objects.create(
            milestone=milestone,
            signed_by=request.user,
            remarks=request.data.get('remarks', '')
        )
        # Auto-complete the milestone on sign-off
        milestone.status = Milestone.Status.COMPLETED
        milestone.save()

        serializer = SignOffSerializer(sign_off)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        if request.user.role != 'project_manager':
            return Response(
                {'error': 'Only project managers can remove sign-offs.'},
                status=status.HTTP_403_FORBIDDEN
            )
        milestone = self.get_milestone(pk)
        if not milestone:
            return Response({'error': 'Milestone not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not hasattr(milestone, 'sign_off'):
            return Response({'error': 'No sign-off found.'}, status=status.HTTP_404_NOT_FOUND)

        milestone.sign_off.delete()
        return Response({'message': 'Sign-off removed.'}, status=status.HTTP_204_NO_CONTENT)


class DeliverableListCreateView(generics.ListCreateAPIView):
    serializer_class   = DeliverableSerializer
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['status', 'milestone']
    ordering_fields    = ['due_date', 'created_at']

    def get_queryset(self):
        return Deliverable.objects.filter(
            milestone_id=self.kwargs['milestone_pk']
        )

    def perform_create(self, serializer):
        milestone = Milestone.objects.get(pk=self.kwargs['milestone_pk'])
        serializer.save(milestone=milestone)


class DeliverableDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = DeliverableSerializer
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_queryset(self):
        return Deliverable.objects.filter(
            milestone_id=self.kwargs['milestone_pk']
        )


class ProjectMilestoneTimelineView(APIView):
    """
    Returns all milestones for a specific project
    ordered for timeline/stepper display.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request, project_pk):
        from projects.models import ProjectMember, Project

        # Check access
        if request.user.role != 'project_manager':
            is_member = ProjectMember.objects.filter(
                user=request.user,
                project_id=project_pk
            ).exists()
            if not is_member:
                return Response(
                    {'error': 'You do not have access to this project.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        milestones = Milestone.objects.filter(
            project_id=project_pk
        ).select_related('owner').prefetch_related('deliverables').order_by('order', 'planned_date')

        serializer = MilestoneDetailSerializer(milestones, many=True)

        # Summary stats
        total     = milestones.count()
        completed = milestones.filter(status='completed').count()
        delayed   = sum(1 for m in milestones if m.is_delayed)

        return Response({
            'project_id': project_pk,
            'summary': {
                'total':     total,
                'completed': completed,
                'pending':   total - completed,
                'delayed':   delayed,
            },
            'milestones': serializer.data,
        })