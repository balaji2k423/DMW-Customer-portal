import os
from django.http import FileResponse, Http404
from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend

from api.throttling import BurstRateThrottle, SustainedRateThrottle, IPRateThrottle
from projects.models import ProjectMember
from .models import Document, DocumentVersion
from .serializers import (
    DocumentListSerializer,
    DocumentDetailSerializer,
    DocumentUploadSerializer,
    DocumentVersionSerializer,
    DocumentVersionUploadSerializer,
)


def get_user_project_ids(user):
    if user.role == 'project_manager':
        return None  # None means all projects
    return ProjectMember.objects.filter(
        user=user
    ).values_list('project_id', flat=True)


class DocumentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    parser_classes     = [MultiPartParser, FormParser]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['category', 'status', 'project', 'file_type', 'is_public']
    search_fields      = ['title', 'description', 'version']
    ordering_fields    = ['created_at', 'title', 'category', 'file_size']

    def get_queryset(self):
        project_ids = get_user_project_ids(self.request.user)
        if project_ids is None:
            return Document.objects.all().select_related('project', 'uploaded_by')
        return Document.objects.filter(
            project_id__in=project_ids
        ).select_related('project', 'uploaded_by')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DocumentUploadSerializer
        return DocumentListSerializer

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]
    parser_classes     = [MultiPartParser, FormParser]

    def get_queryset(self):
        project_ids = get_user_project_ids(self.request.user)
        if project_ids is None:
            return Document.objects.all().select_related('project', 'uploaded_by')
        return Document.objects.filter(
            project_id__in=project_ids
        ).select_related('project', 'uploaded_by')

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return DocumentUploadSerializer
        return DocumentDetailSerializer


class DocumentDownloadView(APIView):
    """
    Serves the file as a download and increments the download counter.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request, pk):
        project_ids = get_user_project_ids(request.user)

        try:
            if project_ids is None:
                doc = Document.objects.get(pk=pk)
            else:
                doc = Document.objects.get(pk=pk, project_id__in=project_ids)
        except Document.DoesNotExist:
            raise Http404

        if not doc.file:
            return Response(
                {'error': 'No file attached to this document.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Increment download count
        Document.objects.filter(pk=pk).update(download_count=doc.download_count + 1)

        file_handle = doc.file.open()
        filename    = os.path.basename(doc.file.name)
        response    = FileResponse(file_handle, as_attachment=True, filename=filename)
        return response


class DocumentVersionListView(generics.ListAPIView):
    """List all versions of a specific document."""
    serializer_class   = DocumentVersionSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get_queryset(self):
        return DocumentVersion.objects.filter(
            document_id=self.kwargs['document_pk']
        ).select_related('uploaded_by')


class DocumentVersionUploadView(APIView):
    """
    Upload a new version of a document.
    Archives the current file as a DocumentVersion before replacing it.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]
    parser_classes     = [MultiPartParser, FormParser]

    def post(self, request, document_pk):
        if request.user.role not in ('project_manager',):
            return Response(
                {'error': 'Only project managers can upload new versions.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            doc = Document.objects.get(pk=document_pk)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DocumentVersionUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Archive the current file as a version
        DocumentVersion.objects.create(
            document    = doc,
            uploaded_by = request.user,
            file        = doc.file,
            version     = doc.version,
            change_note = f'Archived before update to {serializer.validated_data["version"]}',
        )

        # Replace current file with new version
        doc.file    = serializer.validated_data['file']
        doc.version = serializer.validated_data['version']
        if serializer.validated_data.get('change_note'):
            doc.description = serializer.validated_data['change_note']
        doc.save()

        return Response(
            DocumentDetailSerializer(doc, context={'request': request}).data,
            status=status.HTTP_200_OK
        )


class DocumentCategoryListView(APIView):
    """Returns all categories with document counts for folder view."""
    permission_classes = [IsAuthenticated]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]

    def get(self, request):
        from .models import DocumentCategory
        project_ids = get_user_project_ids(request.user)

        categories = []
        for value, label in DocumentCategory.choices:
            if project_ids is None:
                count = Document.objects.filter(category=value).count()
            else:
                count = Document.objects.filter(
                    category=value,
                    project_id__in=project_ids
                ).count()
            categories.append({
                'value': value,
                'label': label,
                'count': count,
            })

        return Response(categories)