from django.urls import path
from .views import (
    DocumentListCreateView,
    DocumentDetailView,
    DocumentDownloadView,
    DocumentVersionListView,
    DocumentVersionUploadView,
    DocumentCategoryListView,
)

urlpatterns = [
    # Categories folder view
    path('categories/',                                  DocumentCategoryListView.as_view(),    name='document-categories'),

    # Documents CRUD
    path('',                                             DocumentListCreateView.as_view(),      name='document-list'),
    path('<int:pk>/',                                    DocumentDetailView.as_view(),          name='document-detail'),

    # Download (increments counter)
    path('<int:pk>/download/',                           DocumentDownloadView.as_view(),        name='document-download'),

    # Version history
    path('<int:document_pk>/versions/',                  DocumentVersionListView.as_view(),     name='document-versions'),
    path('<int:document_pk>/versions/upload/',           DocumentVersionUploadView.as_view(),   name='document-version-upload'),
]