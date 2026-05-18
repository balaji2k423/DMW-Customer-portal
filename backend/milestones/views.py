"""
milestones/views.py
"""

from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from api.throttling import BurstRateThrottle, SustainedRateThrottle, IPRateThrottle
from .models import Milestone, Deliverable, SignOff, Subtask
from .serializers import (
    MilestoneListSerializer,
    MilestoneDetailSerializer,
    MilestoneCreateUpdateSerializer,
    DeliverableSerializer,
    SignOffSerializer,
    SubtaskSerializer,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_accessible_project_ids(user):
    """
    Return a list of project IDs this user may access, or None for full access.

    Rules:
      - admin           → None (skip filter — sees everything)
      - project_manager → only projects where they are a ProjectMember
      - customer_*      → only projects where they are a ProjectMember

    BUG FIX 1: removed Project.objects.filter(company=user) — Project.customer FK
    no longer exists. All membership is tracked through ProjectMember only.

    BUG FIX 2: returns a list instead of a set — Django ORM __in lookups require
    a list or queryset, not a Python set.
    """
    from projects.models import ProjectMember

    if user.role == 'admin':
        return None  # full access — caller skips the queryset filter

    return list(
        ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
    )


def user_is_project_member(user, project_id):
    """Return True if the user belongs to the given project (or is admin)."""
    from projects.models import ProjectMember
    if user.role == 'admin':
        return True
    return ProjectMember.objects.filter(user=user, project_id=project_id).exists()


def _milestone_base_qs():
    """
    Single place that defines the canonical queryset for milestones.
    All views reuse this so prefetches are never forgotten.
    """
    return (
        Milestone.objects
        .select_related('owner', 'project')
        .prefetch_related(
            'deliverables',
            'subtasks',
            'sign_off',
        )
    )


# ─── Customer list ────────────────────────────────────────────────────────────

class CustomerListView(APIView):
    """
    GET /milestones/customers/
    Returns distinct company names from CustomUser accounts with customer roles.
    The `id` field is the company name string itself — this is what the frontend
    passes back as ?customer=<company_name> to filter milestones.

    Admins / project managers → all companies.
    Customer roles            → only their own company (single entry).
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user           = request.user
        CUSTOMER_ROLES = ('customer_admin', 'customer_user')

        if user.role in ('admin', 'project_manager'):
            company_names = (
                User.objects
                .filter(role__in=CUSTOMER_ROLES, is_active=True)
                .exclude(company='')
                .values_list('company', flat=True)
                .distinct()
                .order_by('company')
            )
        elif user.role in CUSTOMER_ROLES:
            company_name  = (user.company or '').strip()
            company_names = [company_name] if company_name else []
        else:
            return Response([])

        customers = [
            {'id': name, 'name': name}
            for name in company_names
            if name and name.strip()
        ]
        return Response(customers)


# ─── Customer-admin list ──────────────────────────────────────────────────────

class CustomerAdminListView(APIView):
    """
    GET /milestones/customer-admins/
    Returns all active users with role=customer_admin.
    Used by the frontend to populate the "Customer Admin" filter dropdown.

    Admins / project managers → all customer_admin users.
    Other roles               → empty list.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user = request.user
        if user.role not in ('admin', 'project_manager'):
            return Response([])

        admins = (
            User.objects
            .filter(role='customer_admin', is_active=True)
            .order_by('first_name', 'last_name')
            .values('id', 'first_name', 'last_name', 'email', 'company')
        )

        result = [
            {
                'id':      u['id'],
                'name':    f"{u['first_name']} {u['last_name']}".strip() or u['email'],
                'email':   u['email'],
                'company': u['company'],
            }
            for u in admins
        ]
        return Response(result)


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
            qs = _milestone_base_qs()
        elif not project_ids:
            return Milestone.objects.none()
        else:
            qs = _milestone_base_qs().filter(project_id__in=project_ids)

        # Optional customer filter: ?customer=<company_name>
        # Find all ProjectMembers whose user.company matches, then filter milestones.
        customer_company = self.request.query_params.get('customer')
        if customer_company:
            from django.contrib.auth import get_user_model
            from projects.models import ProjectMember
            User = get_user_model()
            company_user_ids = list(
                User.objects.filter(company=customer_company, is_active=True)
                .values_list('id', flat=True)
            )
            member_pids = list(
                ProjectMember.objects.filter(user_id__in=company_user_ids)
                .values_list('project_id', flat=True)
            )
            qs = qs.filter(project_id__in=member_pids)

        # Optional customer_admin filter: ?customer_admin_id=<user_id>
        # Scopes milestones to projects where that customer_admin is a member.
        customer_admin_id = self.request.query_params.get('customer_admin_id')
        if customer_admin_id:
            from projects.models import ProjectMember
            ca_project_ids = list(
                ProjectMember.objects.filter(user_id=customer_admin_id)
                .values_list('project_id', flat=True)
            )
            qs = qs.filter(project_id__in=ca_project_ids)

        return qs

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
            return _milestone_base_qs()
        if not project_ids:
            return Milestone.objects.none()
        return _milestone_base_qs().filter(project_id__in=project_ids)

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
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only admins can delete milestones.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)


# ─── Sign-off ─────────────────────────────────────────────────────────────────

class MilestoneSignOffView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def _get_milestone(self, pk, user):
        project_ids = get_accessible_project_ids(user)
        qs = _milestone_base_qs()
        if project_ids is not None:
            qs = qs.filter(project_id__in=project_ids)
        return qs.filter(pk=pk).first()

    def post(self, request, pk):
        milestone = self._get_milestone(pk, request.user)
        if not milestone:
            return Response({'error': 'Milestone not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role not in ('admin', 'project_manager', 'customer_admin'):
            return Response(
                {'error': 'You do not have permission to sign off milestones.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            _ = milestone.sign_off
            return Response(
                {'error': 'Milestone already signed off.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SignOff.DoesNotExist:
            pass

        serializer = SignOffSerializer(data={
            'milestone': milestone.id,
            'remarks':   request.data.get('remarks', ''),
        })
        serializer.is_valid(raise_exception=True)
        serializer.save(signed_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        milestone = self._get_milestone(pk, request.user)
        if not milestone:
            return Response({'error': 'Milestone not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role not in ('admin', 'project_manager'):
            return Response(
                {'error': 'Only admins or project managers can remove sign-offs.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        deleted, _ = SignOff.objects.filter(milestone=milestone).delete()
        if not deleted:
            return Response({'error': 'No sign-off found.'}, status=status.HTTP_404_NOT_FOUND)

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

    def perform_create(self, serializer):
        milestone = Milestone.objects.get(pk=self.kwargs['milestone_pk'])
        serializer.save(milestone=milestone)


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


# ─── Subtasks ─────────────────────────────────────────────────────────────────

class SubtaskListCreateView(generics.ListCreateAPIView):
    serializer_class   = SubtaskSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]
    filter_backends    = [filters.OrderingFilter]
    ordering_fields    = ['order', 'created_at']
    ordering           = ['order']

    def get_queryset(self):
        return Subtask.objects.filter(milestone_id=self.kwargs['milestone_pk'])

    def create(self, request, *args, **kwargs):
        if request.user.role not in ('admin', 'project_manager'):
            return Response(
                {'error': 'Only admins or project managers can add subtasks.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(milestone_id=self.kwargs['milestone_pk'])


class SubtaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = SubtaskSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]
    queryset           = Subtask.objects.select_related('milestone')

    def _check_write(self, request):
        if request.user.role not in ('admin', 'project_manager'):
            return Response(
                {'error': 'Only admins or project managers can modify subtasks.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def update(self, request, *args, **kwargs):
        err = self._check_write(request)
        return err if err else super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        err = self._check_write(request)
        return err if err else super().destroy(request, *args, **kwargs)


class SubtaskReorderView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def post(self, request, milestone_pk):
        if request.user.role not in ('admin', 'project_manager'):
            return Response(
                {'error': 'Only admins or project managers can reorder subtasks.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        ordered_ids = request.data.get('order', [])
        if not isinstance(ordered_ids, list):
            return Response(
                {'error': '`order` must be a list of subtask IDs.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subtasks   = Subtask.objects.filter(milestone_id=milestone_pk, id__in=ordered_ids)
        id_to_obj  = {s.id: s for s in subtasks}

        bulk = []
        for idx, sid in enumerate(ordered_ids):
            obj = id_to_obj.get(sid)
            if obj:
                obj.order = idx
                bulk.append(obj)

        Subtask.objects.bulk_update(bulk, ['order'])
        return Response({'message': 'Reordered successfully.'})


# ─── Timeline ─────────────────────────────────────────────────────────────────

class ProjectMilestoneTimelineView(APIView):
    """
    GET /milestones/project/<project_pk>/timeline/
    Returns all milestones for a project in timeline order.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request, project_pk):
        user        = request.user
        project_ids = get_accessible_project_ids(user)

        if project_ids is not None and int(project_pk) not in project_ids:
            return Response(
                {'error': 'You do not have access to this project.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        milestones = (
            _milestone_base_qs()
            .filter(project_id=project_pk)
            .order_by('order', 'planned_date')
        )

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