from django.urls import path
from .views import (
    DashboardView,
    CustomerListCreateView,
    CustomerDetailView,
    CompanyDropdownView,
    CustomerAdminByCompanyView,
    UserDropdownView,
    ProjectListCreateView,
    ProjectDetailView,
    ProjectMemberListView,
    ProjectMemberDetailView,
)

urlpatterns = [
    # Dashboard
    path('dashboard/',                          DashboardView.as_view(),               name='dashboard'),

    # ── Step 1: Company dropdown for project creation form ────────────────────
    path('companies/dropdown/',                 CompanyDropdownView.as_view(),          name='company-dropdown'),

    # ── Step 2: Customer-admins belonging to a specific company ──────────────
    # Frontend calls this after the admin picks a company.
    # Returns only users with role=customer_admin linked to that company.
    path('companies/<int:company_id>/customer-admins/',
                                                CustomerAdminByCompanyView.as_view(),   name='company-customer-admins'),

    # All-users dropdown (for assigning project_manager / customer_user members)
    path('users/dropdown/',                     UserDropdownView.as_view(),             name='user-dropdown'),

    # Customers (legacy full CRUD)
    path('customers/',                          CustomerListCreateView.as_view(),       name='customer-list'),
    path('customers/<int:pk>/',                 CustomerDetailView.as_view(),           name='customer-detail'),

    # Projects
    path('',                                    ProjectListCreateView.as_view(),        name='project-list'),
    path('<int:pk>/',                           ProjectDetailView.as_view(),            name='project-detail'),

    # Project Members
    path('<int:project_pk>/members/',           ProjectMemberListView.as_view(),        name='project-member-list'),
    path('<int:project_pk>/members/<int:pk>/',  ProjectMemberDetailView.as_view(),      name='project-member-detail'),
]