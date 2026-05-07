# milestones/apps.py

from django.apps import AppConfig


class MilestonesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "milestones"

    def ready(self):
        # Import signals so the @receiver decorators are registered at startup.
        import milestones.signals  # noqa: F401