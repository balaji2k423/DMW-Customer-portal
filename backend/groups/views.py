from rest_framework import generics, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from accounts.models import UserRole
from .models import Group, GroupMember, GroupProject
from .serializers import (
    GroupListSerializer,
    GroupDetailSerializer,
    GroupCreateSerializer,
    GroupMemberSerializer,
    GroupProjectSerializer,
)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == UserRole.ADMIN
        )


# ─── Groups ──────────────────────────────────────────────────────────────────

class GroupListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'description']
    ordering_fields    = ['name', 'created_at']

    def get_queryset(self):
        return Group.objects.prefetch_related('members', 'group_projects').all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return GroupCreateSerializer
        return GroupListSerializer


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = Group.objects.prefetch_related('members__user', 'group_projects__project')
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return GroupCreateSerializer
        return GroupDetailSerializer


# ─── Group Members ────────────────────────────────────────────────────────────

class GroupMemberListView(generics.ListCreateAPIView):
    serializer_class   = GroupMemberSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return GroupMember.objects.filter(
            group_id=self.kwargs['group_pk']
        ).select_related('user')

    def perform_create(self, serializer):
        group = Group.objects.get(pk=self.kwargs['group_pk'])
        serializer.save(group=group)


class GroupMemberDetailView(generics.DestroyAPIView):
    serializer_class   = GroupMemberSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return GroupMember.objects.filter(group_id=self.kwargs['group_pk'])


# ─── Group Projects ───────────────────────────────────────────────────────────

class GroupProjectListView(generics.ListCreateAPIView):
    serializer_class   = GroupProjectSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return GroupProject.objects.filter(
            group_id=self.kwargs['group_pk']
        ).select_related('project__customer')

    def perform_create(self, serializer):
        group = Group.objects.get(pk=self.kwargs['group_pk'])
        serializer.save(group=group)


class GroupProjectDetailView(generics.DestroyAPIView):
    serializer_class   = GroupProjectSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return GroupProject.objects.filter(group_id=self.kwargs['group_pk'])