from rest_framework import serializers
from .models import Company, Customer


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Company
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Customer
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
