from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from api.throttling import BurstRateThrottle, SustainedRateThrottle, IPRateThrottle

from .models import Customer, Project, ProjectMember
from .serializers import (
    CustomerSerializer,
    ProjectListSerializer,
    ProjectDetailSerializer,
    ProjectMemberSerializer,
    DashboardSerializer,
)
from .permissions import IsProjectMember, IsProjectManagerOrReadOnly


class DashboardView(APIView):
    """
    Returns all projects the logged-in user is a member of,
    with summary data for the dashboard hero screen.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request):
        project_ids = ProjectMember.objects.filter(
            user=request.user
        ).values_list('project_id', flat=True)

        projects = Project.objects.filter(id__in=project_ids).select_related('customer')
        serializer = DashboardSerializer(projects, many=True, context={'request': request})
        return Response({
            'count':    len(serializer.data),
            'projects': serializer.data,
        })


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


class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['status', 'customer']
    search_fields      = ['name', 'robot_model', 'contract_number']
    ordering_fields    = ['created_at', 'progress', 'expected_end']

    def get_queryset(self):
        user = self.request.user
        # Project managers see all projects
        if user.role == 'project_manager':
            return Project.objects.all().select_related('customer')
        # Customers see only their assigned projects
        project_ids = ProjectMember.objects.filter(
            user=user
        ).values_list('project_id', flat=True)
        return Project.objects.filter(
            id__in=project_ids
        ).select_related('customer')

    def get_serializer_class(self):
        return ProjectDetailSerializer if self.request.method == 'POST' else ProjectListSerializer


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]
    serializer_class   = ProjectDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'project_manager':
            return Project.objects.all().select_related('customer')
        project_ids = ProjectMember.objects.filter(
            user=user
        ).values_list('project_id', flat=True)
        return Project.objects.filter(id__in=project_ids)


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