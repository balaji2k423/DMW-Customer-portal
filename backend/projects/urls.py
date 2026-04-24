from django.urls import path
from .views import (
    DashboardView,
    CustomerListCreateView,
    CustomerDetailView,
    ProjectListCreateView,
    ProjectDetailView,
    ProjectMemberListView,
    ProjectMemberDetailView,
)

urlpatterns = [
    # Dashboard
    path('dashboard/',                              DashboardView.as_view(),              name='dashboard'),

    # Customers
    path('customers/',                              CustomerListCreateView.as_view(),      name='customer-list'),
    path('customers/<int:pk>/',                     CustomerDetailView.as_view(),          name='customer-detail'),

    # Projects
    path('',                                        ProjectListCreateView.as_view(),       name='project-list'),
    path('<int:pk>/',                               ProjectDetailView.as_view(),           name='project-detail'),

    # Project Members
    path('<int:project_pk>/members/',               ProjectMemberListView.as_view(),       name='project-member-list'),
    path('<int:project_pk>/members/<int:pk>/',      ProjectMemberDetailView.as_view(),     name='project-member-detail'),
]