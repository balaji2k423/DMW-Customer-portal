from django.urls import path
from .views import (
    GroupListCreateView,
    GroupDetailView,
    GroupMemberListView,
    GroupMemberDetailView,
    GroupProjectListView,
    GroupProjectDetailView,
)

urlpatterns = [
    path('',                                          GroupListCreateView.as_view(),  name='group-list'),
    path('<int:pk>/',                                 GroupDetailView.as_view(),      name='group-detail'),
    path('<int:group_pk>/members/',                   GroupMemberListView.as_view(),  name='group-member-list'),
    path('<int:group_pk>/members/<int:pk>/',          GroupMemberDetailView.as_view(),name='group-member-detail'),
    path('<int:group_pk>/projects/',                  GroupProjectListView.as_view(), name='group-project-list'),
    path('<int:group_pk>/projects/<int:pk>/',         GroupProjectDetailView.as_view(),name='group-project-detail'),
]