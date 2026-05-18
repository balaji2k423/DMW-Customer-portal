from django.contrib import admin
from .models import Company, Customer


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display  = ('company_name', 'city', 'state', 'phone_number', 'email')
    search_fields = ('company_name', 'city', 'phone_number')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ['name', 'industry', 'email', 'phone', 'created_at']
    search_fields = ['name', 'industry', 'email']
    ordering      = ['name']
