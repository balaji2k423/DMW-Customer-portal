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
    queryset           = Customer.objects.all()
    serializer_class   = CustomerSerializer
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, SustainedRateThrottle, IPRateThrottle]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'industry', 'email']
    ordering_fields    = ['name', 'created_at']


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = Customer.objects.all()
    serializer_class   = CustomerSerializer
    permission_classes = [IsAuthenticated, IsProjectManagerOrReadOnly]
    throttle_classes   = [BurstRateThrottle, IPRateThrottle]
