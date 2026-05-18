"""
Migration: replace Project.customer (FK → CustomUser) with
           Project.company  (FK → companies.Company)

Run:
    python manage.py migrate projects

If you have existing data you want to preserve, fill in the data migration
section below before running.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        # ── adjust these to your actual last migrations ───────────────────────
        ('projects', '0001_initial'),          # your current latest projects migration
        ('company_master', '0001_initial'),           # company app must exist first
    ]

    operations = [
        # 1. Remove the old unique constraint that referenced `customer`
        migrations.RemoveConstraint(
            model_name='project',
            name='unique_project_name_per_customer',
        ),

        # 2. Remove the old customer FK
        migrations.RemoveField(
            model_name='project',
            name='customer',
        ),

        # 3. Add the new company FK
        migrations.AddField(
            model_name='project',
            name='company',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='projects',
                to='company_master.company',
            ),
        ),

        # 4. Re-add the unique constraint for (company, name)
        migrations.AddConstraint(
            model_name='project',
            constraint=models.UniqueConstraint(
                fields=['company', 'name'],
                name='unique_project_name_per_company',
            ),
        ),
    ]