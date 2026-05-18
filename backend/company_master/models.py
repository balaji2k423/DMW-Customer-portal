from django.db import models


class Company(models.Model):
    company_name  = models.CharField(max_length=255)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city          = models.CharField(max_length=100)
    state         = models.CharField(max_length=100)
    pincode       = models.CharField(max_length=10)
    phone_number  = models.CharField(max_length=15)
    email         = models.EmailField(blank=True, null=True)
    website       = models.URLField(blank=True, null=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Company"
        verbose_name_plural = "Companies"
        ordering            = ['company_name']

    def __str__(self):
        return self.company_name


class Customer(models.Model):
    name       = models.CharField(max_length=200)
    industry   = models.CharField(max_length=100, blank=True)
    address    = models.TextField(blank=True)
    phone      = models.CharField(max_length=20, blank=True)
    email      = models.EmailField(blank=True)
    website    = models.URLField(blank=True)
    logo       = models.ImageField(upload_to='customer_logos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
