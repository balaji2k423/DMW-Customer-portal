from django.urls import path
from .views import (
    CustomerListView,
    CustomerAdminListView,
    MilestoneListCreateView,
    MilestoneDetailView,
    MilestoneSignOffView,
    DeliverableListCreateView,
    DeliverableDetailView,
    ProjectMilestoneTimelineView,
    SubtaskListCreateView,
    SubtaskDetailView,
    SubtaskReorderView,
)

urlpatterns = [
    # ── Customer lookup ───────────────────────────────────────────────────────
    path('customers/',
         CustomerListView.as_view(),
         name='milestone-customers'),

    # ── Customer-admin lookup ─────────────────────────────────────────────────
    path('customer-admins/',
         CustomerAdminListView.as_view(),
         name='milestone-customer-admins'),

    # ── Timeline for a specific project ──────────────────────────────────────
    path('project/<int:project_pk>/timeline/',
         ProjectMilestoneTimelineView.as_view(),
         name='milestone-timeline'),

    # ── Milestones CRUD ───────────────────────────────────────────────────────
    path('',
         MilestoneListCreateView.as_view(),
         name='milestone-list'),

    path('<int:pk>/',
         MilestoneDetailView.as_view(),
         name='milestone-detail'),

    # ── Sign-off ──────────────────────────────────────────────────────────────
    path('<int:pk>/signoff/',
         MilestoneSignOffView.as_view(),
         name='milestone-signoff'),

    # ── Deliverables nested under milestone ───────────────────────────────────
    path('<int:milestone_pk>/deliverables/',
         DeliverableListCreateView.as_view(),
         name='deliverable-list'),

    path('<int:milestone_pk>/deliverables/<int:pk>/',
         DeliverableDetailView.as_view(),
         name='deliverable-detail'),

    # ── Subtasks nested under milestone ───────────────────────────────────────
    path('<int:milestone_pk>/subtasks/',
         SubtaskListCreateView.as_view(),
         name='subtask-list'),

    path('<int:milestone_pk>/subtasks/reorder/',
         SubtaskReorderView.as_view(),
         name='subtask-reorder'),
]

# ── Subtask detail (standalone — PATCH /subtasks/<pk>/ used by frontend) ──────
# These live outside the milestone prefix so the service can call
# /subtasks/<id>/ directly without knowing milestone_pk.
subtask_detail_urlpatterns = [
    path('<int:pk>/',
         SubtaskDetailView.as_view(),
         name='subtask-detail'),
]