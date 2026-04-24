from django.urls import path
from .views import (
    MilestoneListCreateView,
    MilestoneDetailView,
    MilestoneSignOffView,
    DeliverableListCreateView,
    DeliverableDetailView,
    ProjectMilestoneTimelineView,
)

urlpatterns = [
    # Timeline for a specific project
    path('project/<int:project_pk>/timeline/',       ProjectMilestoneTimelineView.as_view(),  name='milestone-timeline'),

    # Milestones CRUD
    path('',                                         MilestoneListCreateView.as_view(),       name='milestone-list'),
    path('<int:pk>/',                                MilestoneDetailView.as_view(),           name='milestone-detail'),

    # Sign-off
    path('<int:pk>/signoff/',                        MilestoneSignOffView.as_view(),          name='milestone-signoff'),

    # Deliverables nested under milestone
    path('<int:milestone_pk>/deliverables/',         DeliverableListCreateView.as_view(),     name='deliverable-list'),
    path('<int:milestone_pk>/deliverables/<int:pk>/', DeliverableDetailView.as_view(),        name='deliverable-detail'),
]