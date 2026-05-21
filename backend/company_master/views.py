# company_master/views.py

from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from api.throttling import BurstRateThrottle, SustainedRateThrottle, IPRateThrottle

from .models import Company, Customer
from .serializers import CompanySerializer, CustomerSerializer
from projects.permissions import IsProjectManagerOrReadOnly

User = get_user_model()


class CompanyListCreateView(generics.ListCreateAPIView):
    queryset           = Company.objects.all()
    serializer_class   = CompanySerializer
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['company_name', 'city', 'email']
    ordering_fields    = ['company_name', 'created_at']


class CompanyDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = Company.objects.all()
    serializer_class   = CompanySerializer
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]


class CustomerListCreateView(generics.ListCreateAPIView):
    serializer_class   = CustomerSerializer
    # FIX: IsAuthenticated alone for reads so guest/customer roles can fetch
    # the customer list when building permissions. Write operations are still
    # restricted to project_manager / admin by IsProjectManagerOrReadOnly.
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'industry', 'email']
    ordering_fields    = ['name', 'created_at']

    def get_queryset(self):
        qs = Customer.objects.select_related('company').all()

        company_id = self.request.query_params.get('company_id')
        if company_id:
            # FIX: guard against non-integer values to avoid unhandled ValueError
            try:
                company_id_int = int(company_id)
            except (ValueError, TypeError):
                return qs.none()
            qs = qs.filter(company_id=company_id_int)

        return qs


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = Customer.objects.select_related('company').all()
    serializer_class   = CustomerSerializer
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]