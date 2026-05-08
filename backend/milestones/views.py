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


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_accessible_project_ids(user):
    """
    Return the set of project IDs this user may access, or None for full access.

    Rules:
      - admin            → None (skip filter — sees everything)
      - project_manager  → only projects where they are a ProjectMember
      - customer_admin   → projects where they are the customer FK OR a ProjectMember
      - customer_user    → projects where they are the customer FK OR a ProjectMember
    """
    from projects.models import ProjectMember, Project

    if user.role == 'admin':
        return None  # full access — caller skips the queryset filter

    member_project_ids = list(
        ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
    )

    if user.role == 'project_manager':
        # PM only sees projects they are explicitly a member of
        return set(member_project_ids)

    # customer_admin / customer_user
    customer_project_ids = list(
        Project.objects.filter(customer=user).values_list('id', flat=True)
    )
    return set(customer_project_ids) | set(member_project_ids)


def user_is_project_member(user, project_id):
    """Return True if the user belongs to the given project (or is admin)."""
    from projects.models import ProjectMember
    if user.role == 'admin':
        return True
    return ProjectMember.objects.filter(user=user, project_id=project_id).exists()


# ─── Milestones ───────────────────────────────────────────────────────────────

class MilestoneListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields   = ['status', 'project']
    search_fields      = ['title', 'description']
    ordering_fields    = ['planned_date', 'order', 'created_at']

    def get_queryset(self):
        user        = self.request.user
        project_ids = get_accessible_project_ids(user)

        if project_ids is None:
            return Milestone.objects.all().select_related('owner', 'project')

        if not project_ids:
            return Milestone.objects.none()

        return Milestone.objects.filter(
            project_id__in=project_ids
        ).select_related('owner', 'project')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MilestoneCreateUpdateSerializer
        return MilestoneListSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role not in ('admin', 'project_manager'):
            return Response(
                {'error': 'Only admins or project managers can create milestones.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        project_id = request.data.get('project')
        if project_id and not user_is_project_member(request.user, project_id):
            return Response(
                {'error': 'You are not a member of this project.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)


class MilestoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_queryset(self):
        user        = self.request.user
        project_ids = get_accessible_project_ids(user)

        if project_ids is None:
            return Milestone.objects.all().select_related('owner', 'project')

        if not project_ids:
            return Milestone.objects.none()

        return Milestone.objects.filter(
            project_id__in=project_ids
        ).select_related('owner', 'project')

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return MilestoneCreateUpdateSerializer
        return MilestoneDetailSerializer

    def update(self, request, *args, **kwargs):
        milestone = self.get_object()
        if request.user.role not in ('admin', 'project_manager'):
            return Response(
                {'error': 'Only admins or project managers can edit milestones.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not user_is_project_member(request.user, milestone.project_id):
            return Response(
                {'error': 'You are not a member of this project.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        milestone = self.get_object()
        if request.user.role not in ('admin', 'project_manager'):
            return Response(
                {'error': 'Only admins or project managers can delete milestones.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not user_is_project_member(request.user, milestone.project_id):
            return Response(
                {'error': 'You are not a member of this project.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)


# ─── Sign-off ─────────────────────────────────────────────────────────────────

class MilestoneSignOffView(APIView):
    """
    POST   — customer_admin (who is a project member) signs off a milestone.
    DELETE — admin or project_manager (who is a project member) removes a sign-off.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_milestone(self, pk):
        try:
            return Milestone.objects.select_related('project').get(pk=pk)
        except Milestone.DoesNotExist:
            return None

    def post(self, request, pk):
        if request.user.role != 'customer_admin':
            return Response(
                {'error': 'Only customer admins can sign off milestones.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        milestone = self.get_milestone(pk)
        if not milestone:
            return Response({'error': 'Milestone not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not user_is_project_member(request.user, milestone.project_id):
            return Response(
                {'error': 'You are not a member of this project.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if hasattr(milestone, 'sign_off'):
            return Response(
                {'error': 'This milestone has already been signed off.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sign_off = SignOff.objects.create(
            milestone=milestone,
            signed_by=request.user,
            remarks=request.data.get('remarks', ''),
        )
        milestone.status = Milestone.Status.COMPLETED
        milestone.save()

        return Response(SignOffSerializer(sign_off).data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        if request.user.role not in ('admin', 'project_manager'):
            return Response(
                {'error': 'Only admins or project managers can remove sign-offs.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        milestone = self.get_milestone(pk)
        if not milestone:
            return Response({'error': 'Milestone not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not user_is_project_member(request.user, milestone.project_id):
            return Response(
                {'error': 'You are not a member of this project.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not hasattr(milestone, 'sign_off'):
            return Response({'error': 'No sign-off found.'}, status=status.HTTP_404_NOT_FOUND)

        milestone.sign_off.delete()
        return Response({'message': 'Sign-off removed.'}, status=status.HTTP_204_NO_CONTENT)


# ─── Deliverables ─────────────────────────────────────────────────────────────

class DeliverableListCreateView(generics.ListCreateAPIView):
    serializer_class   = DeliverableSerializer
    permission_classes = [IsAuthenticated]
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

    def create(self, request, *args, **kwargs):
        if request.user.role not in ('admin', 'project_manager'):
            return Response(
                {'error': 'Only admins or project managers can add deliverables.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        milestone = Milestone.objects.filter(pk=self.kwargs['milestone_pk']).first()
        if milestone and not user_is_project_member(request.user, milestone.project_id):
            return Response(
                {'error': 'You are not a member of this project.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)


class DeliverableDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = DeliverableSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_queryset(self):
        return Deliverable.objects.filter(
            milestone_id=self.kwargs['milestone_pk']
        )

    def _check_write_permission(self, request, deliverable):
        if request.user.role not in ('admin', 'project_manager'):
            return Response(
                {'error': 'Only admins or project managers can modify deliverables.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not user_is_project_member(request.user, deliverable.milestone.project_id):
            return Response(
                {'error': 'You are not a member of this project.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def update(self, request, *args, **kwargs):
        err = self._check_write_permission(request, self.get_object())
        return err if err else super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        err = self._check_write_permission(request, self.get_object())
        return err if err else super().destroy(request, *args, **kwargs)


# ─── Timeline ─────────────────────────────────────────────────────────────────

class ProjectMilestoneTimelineView(APIView):
    """
    GET /project/<project_pk>/timeline/
    Returns all milestones for a project in timeline order.
    Access: project members only (admin bypasses membership check).
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request, project_pk):
        user        = request.user
        project_ids = get_accessible_project_ids(user)

        # None = admin (full access); otherwise verify membership
        if project_ids is not None and int(project_pk) not in project_ids:
            return Response(
                {'error': 'You do not have access to this project.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        milestones = Milestone.objects.filter(
            project_id=project_pk
        ).select_related('owner').prefetch_related('deliverables').order_by('order', 'planned_date')

        serializer = MilestoneDetailSerializer(milestones, many=True)

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