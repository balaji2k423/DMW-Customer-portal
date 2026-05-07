from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from api.throttling import BurstRateThrottle, SustainedRateThrottle, IPRateThrottle

from .models import Customer, Project, ProjectMember
from .serializers import (
    CustomerSerializer,
    CustomerDropdownSerializer,
    UserDropdownSerializer,
    ProjectListSerializer,
    ProjectDetailSerializer,
    ProjectMemberSerializer,
    DashboardSerializer,
)
from .permissions import IsProjectMember, IsProjectManagerOrReadOnly

User = get_user_model()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_customer_projects(user):
    """
    Returns projects visible to a customer:
      - projects where they are the customer FK (owner), OR
      - projects where they are a ProjectMember
    Uses .distinct() to avoid duplicates when both conditions are true.
    """
    member_project_ids = ProjectMember.objects.filter(
        user=user
    ).values_list('project_id', flat=True)

    return Project.objects.filter(
        Q(customer=user) | Q(id__in=member_project_ids)
    ).select_related('customer').prefetch_related('members').distinct()


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request):
        user = request.user
        if user.role in ('project_manager', 'admin'):
            projects = Project.objects.all().select_related('customer')
        else:
            projects = get_customer_projects(user)

        serializer = DashboardSerializer(projects, many=True, context={'request': request})
        return Response({'count': len(serializer.data), 'projects': serializer.data})


# ─── Dropdown helpers (used by the frontend create-project form) ───────────────

class CustomerDropdownView(generics.ListAPIView):
    """
    GET /projects/customers/dropdown/
    Returns CustomUser records with customer_admin or customer_user role.
    Shape: [{ id, name }] where name = company (if set) else full_name.
    The frontend sends user.id as Project.customer FK.
    """
    serializer_class   = CustomerDropdownSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle]
    pagination_class   = None

    def get_queryset(self):
        return User.objects.filter(
            role__in=['customer_admin', 'customer_user'],
            is_active=True,
        ).order_by('company', 'first_name', 'last_name')


class UserDropdownView(generics.ListAPIView):
    """GET /projects/users/dropdown/ — returns all users for member assignment."""
    serializer_class   = UserDropdownSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle]
    pagination_class   = None

    def get_queryset(self):
        return User.objects.filter(is_active=True).order_by('first_name', 'last_name')


# ─── Customers (legacy — kept for other parts of the system) ──────────────────

class CustomerListCreateView(generics.ListCreateAPIView):
    queryset           = Customer.objects.all()
    serializer_class   = CustomerSerializer
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'industry', 'email']
    ordering_fields    = ['name', 'created_at']


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = Customer.objects.all()
    serializer_class   = CustomerSerializer
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]


# ─── Projects ─────────────────────────────────────────────────────────────────

class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['status', 'customer']
    search_fields      = ['name', 'robot_model', 'contract_number']
    ordering_fields    = ['created_at', 'progress', 'expected_end']

    def get_queryset(self):
        user = self.request.user
        if user.role in ('project_manager', 'admin'):
            return Project.objects.all().select_related('customer').prefetch_related('members')
        # Customers see projects where they are the owner FK OR a member
        return get_customer_projects(user)

    def get_serializer_class(self):
        return ProjectDetailSerializer if self.request.method == 'POST' else ProjectListSerializer


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]
    serializer_class   = ProjectDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ('project_manager', 'admin'):
            return Project.objects.all().select_related('customer').prefetch_related('members')
        # Customers see projects where they are the owner FK OR a member
        return get_customer_projects(user)


# ─── Project Members ──────────────────────────────────────────────────────────

class ProjectMemberListView(generics.ListCreateAPIView):
    serializer_class   = ProjectMemberSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_queryset(self):
        return ProjectMember.objects.filter(
            project_id=self.kwargs['project_pk']
        ).select_related('user')

    def perform_create(self, serializer):
        project = Project.objects.get(pk=self.kwargs['project_pk'])
        serializer.save(project=project)


class ProjectMemberDetailView(generics.RetrieveDestroyAPIView):
    serializer_class   = ProjectMemberSerializer
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_queryset(self):
        return ProjectMember.objects.filter(
            project_id=self.kwargs['project_pk']
        )