from django.urls import path
from .views import (
    DashboardView,
    CustomerListCreateView,
    CustomerDetailView,
    CustomerDropdownView,
    UserDropdownView,
    ProjectListCreateView,
    ProjectDetailView,
    ProjectMemberListView,
    ProjectMemberDetailView,
)

urlpatterns = [
    # Dashboard
    path('dashboard/',                          DashboardView.as_view(),              name='dashboard'),

    # Dropdown helpers — used by the frontend create/edit project form
    path('customers/dropdown/',                 CustomerDropdownView.as_view(),        name='customer-dropdown'),
    path('users/dropdown/',                     UserDropdownView.as_view(),            name='user-dropdown'),

    # Customers (full CRUD)
    path('customers/',                          CustomerListCreateView.as_view(),      name='customer-list'),
    path('customers/<int:pk>/',                 CustomerDetailView.as_view(),          name='customer-detail'),

    # Projects
    path('',                                    ProjectListCreateView.as_view(),       name='project-list'),
    path('<int:pk>/',                           ProjectDetailView.as_view(),           name='project-detail'),

    # Project Members
    path('<int:project_pk>/members/',           ProjectMemberListView.as_view(),       name='project-member-list'),
    path('<int:project_pk>/members/<int:pk>/',  ProjectMemberDetailView.as_view(),     name='project-member-detail'),
]