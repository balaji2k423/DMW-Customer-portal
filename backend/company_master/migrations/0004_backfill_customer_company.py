from django.db import migrations


def backfill(apps, schema_editor):
    Customer = apps.get_model('company_master', 'Customer')
    Company  = apps.get_model('company_master', 'Company')
    default_company = Company.objects.order_by('id').first()
    if default_company:
        Customer.objects.filter(company__isnull=True).update(company=default_company)


def reverse_backfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('company_master', '0003_customer_company'),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_backfill),
    ]