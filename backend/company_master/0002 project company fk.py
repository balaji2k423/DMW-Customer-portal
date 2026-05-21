"""
Migration: add company FK to company_master.Customer
Run after copying models.py into your company_master app:

    python manage.py makemigrations company_master
    python manage.py migrate

Or apply this file manually as:
    company_master/migrations/0002_customer_company.py
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        # Replace '0001_initial' with your actual last migration name
        ('company_master', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='company',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='customers',
                to='company_master.company',
            ),
        ),
    ]