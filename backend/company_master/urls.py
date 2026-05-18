# company_master/urls.py

from django.urls import path
from .views import (
    CompanyListCreateView, CompanyDetailView,
    CustomerListCreateView, CustomerDetailView,
)

urlpatterns = [
    path('companies/',           CompanyListCreateView.as_view(), name='company-list'),
    path('companies/<int:pk>/',  CompanyDetailView.as_view(),     name='company-detail'),
    path('customers/',           CustomerListCreateView.as_view(), name='customer-list'),
    path('customers/<int:pk>/',  CustomerDetailView.as_view(),    name='customer-detail'),
]