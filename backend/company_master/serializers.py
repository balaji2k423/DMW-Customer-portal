from rest_framework import serializers
from .models import Company, Customer


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Company
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomerSerializer(serializers.ModelSerializer):
    # Expose company_id as a plain integer for easy FK assignment and frontend use.
    # The nested company object is available read-only via company_detail.
    company_id     = serializers.PrimaryKeyRelatedField(
        source='company',
        queryset=Company.objects.all(),
        required=False,
        allow_null=True,
    )
    company_detail = CompanySerializer(source='company', read_only=True)

    class Meta:
        model  = Customer
        fields = [
            'id',
            'company_id',
            'company_detail',
            'name',
            'industry',
            'address',
            'phone',
            'email',
            'website',
            'logo',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'company_detail']