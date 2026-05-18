"""
Manual migration — copy to your accounts/migrations/ folder and run:
    python manage.py migrate accounts
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        # Replace with your actual last migration name, e.g.:
        # ('accounts', '0003_mfa_enabled'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        # 1. Add 'guest' to the role field choices
        #    (Django TextChoices are stored as plain strings, so no DB change
        #     is strictly necessary for Postgres/SQLite — the migration is
        #     provided for completeness and to keep the migration history clean.)
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[
                    ('admin',           'Admin'),
                    ('customer_admin',  'Customer Admin'),
                    ('customer_user',   'Customer User'),
                    ('project_manager', 'Project Manager'),
                    ('guest',           'Guest'),
                ],
                default='customer_user',
                max_length=20,
            ),
        ),

        # 2. Create the GuestPermission table
        migrations.CreateModel(
            name='GuestPermission',
            fields=[
                ('id',          models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('module',      models.CharField(
                    choices=[
                        ('dashboard',  'Dashboard'),
                        ('tickets',    'Tickets'),
                        ('milestones', 'Milestones'),
                    ],
                    max_length=30,
                )),
                ('project_id',  models.IntegerField(blank=True, null=True)),
                ('customer_id', models.IntegerField(blank=True, null=True)),
                ('guest',       models.ForeignKey(
                    limit_choices_to={'role': 'guest'},
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='guest_permissions',
                    to='accounts.customuser',
                )),
            ],
            options={
                'ordering': ['module'],
                'unique_together': {('guest', 'module', 'project_id', 'customer_id')},
            },
        ),
    ]