# documents/views.py

import os
from django.http import FileResponse, Http404
from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend

from api.throttling import BurstRateThrottle, SustainedRateThrottle, IPRateThrottle
from projects.models import ProjectMember, Project
from .models import Document, DocumentVersion
from .serializers import (
    DocumentListSerializer,
    DocumentDetailSerializer,
    DocumentUploadSerializer,
    DocumentVersionSerializer,
    DocumentVersionUploadSerializer,
)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


def get_user_accessible_project_ids(user):
    """
    Returns:
      - None  → admin (unrestricted, sees all projects)
      - list  → project IDs the user can see via ProjectMember membership

    Scoping rules:
      admin           → None (all projects)
      project_manager → projects they are explicitly a ProjectMember of
      customer_*      → projects they are a ProjectMember of
      guest           → projects they are a ProjectMember of
                        (admin grants guest access by adding them as a ProjectMember)
    """
    if user.role == 'admin':
        return None  # unrestricted

    return list(
        ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
    )


def _can_upload(user):
    """
    Upload rules:
      - admin           : always yes
      - project_manager : yes (own projects enforced separately in create())
      - customer_admin  : yes
      - customer_user   : yes
      - guest           : yes ONLY if admin has granted them document-page access
                          (tracked via GuestPermission with module='documents')
    """
    if user.role in ('admin', 'project_manager', 'customer_admin', 'customer_user'):
        return True

    if user.role == 'guest':
        # FIX: guests may upload only when admin has explicitly granted document access.
        # Previously guest upload was blocked entirely.
        try:
            from accounts.models import GuestPermission
            return GuestPermission.objects.filter(
                guest=user,
                module='documents',
            ).exists()
        except Exception:
            return False

    return False


def _can_edit_or_delete(user):
    """
    Edit / delete rules: only admin and project_manager.
    FIX: previously the inline role check used ('admin', 'project_manager')
    correctly, but it was duplicated across three methods without a shared
    helper. Centralised here so future role changes only need one edit.
    """
    return user.role in ('admin', 'project_manager')


def _doc_queryset(user, customer_admin_id=None):
    """Shared filtered queryset for documents."""
    project_ids = get_user_accessible_project_ids(user)
    qs = Document.objects.select_related('project', 'uploaded_by')

    if project_ids is None:
        qs = qs.all()
    else:
        qs = qs.filter(project_id__in=project_ids)

    if customer_admin_id:
        ca_project_ids = list(
            ProjectMember.objects.filter(user_id=customer_admin_id)
            .values_list('project_id', flat=True)
        )
        qs = qs.filter(project_id__in=ca_project_ids)

    return qs


def _check_upload_size(request):
    """Returns an error Response if the uploaded file exceeds 5 MB, else None."""
    f = request.FILES.get('file')
    if f and f.size > MAX_UPLOAD_BYTES:
        return Response(
            {'error': f'File size {f.size / 1024 / 1024:.1f} MB exceeds the 5 MB limit.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


class DocumentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    parser_classes     = [MultiPartParser, FormParser]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['category', 'status', 'project', 'file_type', 'is_public']
    search_fields      = ['title', 'description', 'version']
    ordering_fields    = ['created_at', 'title', 'category', 'file_size']

    def get_queryset(self):
        customer_admin_id = self.request.query_params.get('customer_admin_id')
        return _doc_queryset(self.request.user, customer_admin_id=customer_admin_id)

    def get_serializer_class(self):
        return DocumentUploadSerializer if self.request.method == 'POST' else DocumentListSerializer

    def create(self, request, *args, **kwargs):
        # FIX: replaced hardcoded ('admin', 'project_manager') check with _can_upload()
        # so that customer_admin, customer_user, and permitted guests can also upload.
        if not _can_upload(request.user):
            return Response(
                {'error': 'You do not have permission to upload documents.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        size_err = _check_upload_size(request)
        if size_err:
            return size_err

        # project_manager can only upload to their own assigned projects.
        if request.user.role == 'project_manager':
            project_id = request.data.get('project')
            if project_id:
                allowed = get_user_accessible_project_ids(request.user)
                if allowed is not None and int(project_id) not in allowed:
                    return Response(
                        {'error': 'You can only upload documents to projects you are assigned to.'},
                        status=status.HTTP_403_FORBIDDEN,
                    )

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]
    parser_classes     = [MultiPartParser, FormParser]

    def get_queryset(self):
        return _doc_queryset(self.request.user)

    def get_serializer_class(self):
        return DocumentUploadSerializer if self.request.method in ('PUT', 'PATCH') else DocumentDetailSerializer

    def update(self, request, *args, **kwargs):
        # FIX: edit restricted to admin and project_manager only (rule unchanged,
        # but now uses the shared _can_edit_or_delete helper for consistency).
        if not _can_edit_or_delete(request.user):
            return Response(
                {'error': 'Only admins and project managers can edit documents.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        size_err = _check_upload_size(request)
        if size_err:
            return size_err
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # FIX: delete restricted to admin and project_manager only.
        if not _can_edit_or_delete(request.user):
            return Response(
                {'error': 'Only admins and project managers can delete documents.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)


class DocumentDownloadView(APIView):
    """Serves the file as a download and increments the download counter."""
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request, pk):
        try:
            doc = _doc_queryset(request.user).get(pk=pk)
        except Document.DoesNotExist:
            raise Http404

        if not doc.file:
            return Response({'error': 'No file attached.'}, status=status.HTTP_404_NOT_FOUND)

        Document.objects.filter(pk=pk).update(download_count=doc.download_count + 1)

        file_handle = doc.file.open()
        filename    = os.path.basename(doc.file.name)
        return FileResponse(file_handle, as_attachment=True, filename=filename)


class DocumentVersionListView(generics.ListAPIView):
    """List all archived versions of a document."""
    serializer_class   = DocumentVersionSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_queryset(self):
        try:
            _doc_queryset(self.request.user).get(pk=self.kwargs['document_pk'])
        except Document.DoesNotExist:
            raise Http404
        return DocumentVersion.objects.filter(
            document_id=self.kwargs['document_pk']
        ).select_related('uploaded_by')


class DocumentVersionUploadView(APIView):
    """
    POST /documents/<id>/versions/upload/

    Bumps the document to a new version:
      1. Archives the current file + version tag as a DocumentVersion row.
      2. Replaces Document.file and Document.version with the new upload.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request, document_pk):
        # Version upload is an edit operation — admin and project_manager only.
        if not _can_edit_or_delete(request.user):
            return Response(
                {'error': 'Only admins and project managers can upload new versions.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        size_err = _check_upload_size(request)
        if size_err:
            return size_err

        try:
            doc = _doc_queryset(request.user).get(pk=document_pk)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DocumentVersionUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_version = serializer.validated_data['version']
        new_file    = serializer.validated_data['file']
        change_note = serializer.validated_data.get('change_note', '')

        # Archive current state
        DocumentVersion.objects.create(
            document    = doc,
            uploaded_by = request.user,
            file        = doc.file,
            version     = doc.version,
            change_note = change_note or f'Archived before update to {new_version}',
        )

        # Promote new file
        doc.file    = new_file
        doc.version = new_version
        if change_note:
            doc.description = change_note
        doc.save()

        return Response(
            DocumentDetailSerializer(doc, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )


class DocumentCategoryListView(APIView):
    """Returns all categories with document counts scoped to the requesting user."""
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request):
        from .models import DocumentCategory
        project_ids = get_user_accessible_project_ids(request.user)

        categories = []
        for value, label in DocumentCategory.choices:
            qs = Document.objects.filter(category=value)
            if project_ids is not None:
                qs = qs.filter(project_id__in=project_ids)
            categories.append({'value': value, 'label': label, 'count': qs.count()})

        return Response(categories)