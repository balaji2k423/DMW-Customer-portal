# projects/views.py

from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from api.throttling import BurstRateThrottle, SustainedRateThrottle, IPRateThrottle

from .models import Customer, Project, ProjectMember
from .serializers import (
    CustomerSerializer,
    CompanyDropdownSerializer,
    CustomerAdminDropdownSerializer,
    UserDropdownSerializer,
    ProjectListSerializer,
    ProjectDetailSerializer,
    ProjectMemberSerializer,
    DashboardSerializer,
)
from .permissions import IsProjectMember, IsProjectManagerOrReadOnly, IsAdminOrReadOnly

from company_master.models import Company

User = get_user_model()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_customer_projects(user):
    """
    Returns projects visible to a non-admin user.
    Membership is tracked entirely through ProjectMember.
    """
    member_project_ids = ProjectMember.objects.filter(
        user=user
    ).values_list('project_id', flat=True)

    return (
        Project.objects
        .filter(id__in=member_project_ids)
        .select_related('company')
        .prefetch_related('members')
        .distinct()
    )


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request):
        user = request.user
        # FIX: only admin gets the unrestricted project list on the dashboard.
        # project_manager was incorrectly given admin-level access here.
        if user.role == 'admin':
            projects = (
                Project.objects.all()
                .select_related('company')
                .prefetch_related('members')
            )
        else:
            projects = get_customer_projects(user)

        serializer = DashboardSerializer(projects, many=True, context={'request': request})
        return Response({'count': len(serializer.data), 'projects': serializer.data})


# ─── Company dropdown (Step 1 of project creation) ────────────────────────────

class CompanyDropdownView(generics.ListAPIView):
    """
    GET /projects/companies/dropdown/
    Shape: [{ id, company_name, city, state }]
    """
    serializer_class   = CompanyDropdownSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle]
    pagination_class   = None

    def get_queryset(self):
        return Company.objects.all().order_by('company_name')


# ─── Customer-admin dropdown (Step 2 — filtered by company) ──────────────────

class CustomerAdminByCompanyView(generics.ListAPIView):
    """
    GET /projects/companies/<company_id>/customer-admins/
    Shape: [{ id, email, full_name }]
    """
    serializer_class   = CustomerAdminDropdownSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle]
    pagination_class   = None

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        try:
            company = Company.objects.get(pk=company_id)
        except Company.DoesNotExist:
            return User.objects.none()

        return (
            User.objects
            .filter(
                role='customer_admin',
                is_active=True,
                company=company.company_name,
            )
            # Prefetch memberships so get_project_ids() hits the cache, not the DB
            .prefetch_related('project_memberships')
            .order_by('first_name', 'last_name')
        )


# ─── User dropdown (for assigning all team members) ───────────────────────────

class UserDropdownView(generics.ListAPIView):
    """GET /projects/users/dropdown/ — returns all active users for member assignment."""
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
    # project_manager may still manage Customer records (not Project records).
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
    # FIX: IsAdminOrReadOnly — only admin may POST (create) a project.
    # Previously IsProjectManagerOrReadOnly incorrectly allowed project_manager to create.
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['status', 'company']
    search_fields      = ['name', 'robot_model', 'contract_number']
    ordering_fields    = ['created_at', 'progress', 'expected_end']

    def get_queryset(self):
        user = self.request.user
        # FIX: only admin gets the unrestricted queryset.
        # project_manager was incorrectly treated as elevated here.
        if user.role == 'admin':
            return (
                Project.objects.all()
                .select_related('company')
                .prefetch_related('members')
            )
        return get_customer_projects(user)

    def get_serializer_class(self):
        return ProjectDetailSerializer if self.request.method == 'POST' else ProjectListSerializer


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    # FIX: IsAdminOrReadOnly — only admin may PUT/PATCH/DELETE a project.
    # Previously IsProjectManagerOrReadOnly incorrectly allowed project_manager to edit/delete.
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]
    serializer_class   = ProjectDetailSerializer

    def get_queryset(self):
        user = self.request.user
        # FIX: only admin gets the unrestricted queryset.
        if user.role == 'admin':
            return (
                Project.objects.all()
                .select_related('company')
                .prefetch_related('members')
            )
        return get_customer_projects(user)


# ─── Project Members ──────────────────────────────────────────────────────────

class ProjectMemberListView(generics.ListCreateAPIView):
    serializer_class   = ProjectMemberSerializer
    # FIX: was [IsAuthenticated] alone — any logged-in user could POST (add members).
    # Now only admin can add project members.
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
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
    # FIX: was IsProjectManagerOrReadOnly — project_manager could delete members.
    # Now only admin can remove a project member.
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_queryset(self):
        return ProjectMember.objects.filter(
            project_id=self.kwargs['project_pk']
        )