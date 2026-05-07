"""
milestones/signals.py

Automatically creates 7 standard milestones whenever a new Project is saved.

The planned_date for each milestone is derived from the project's start_date.
If no start_date is set we fall back to today. Each milestone is spaced
WEEK_OFFSET weeks apart from the previous one.
"""

from datetime import timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from projects.models import Project
from .models import Milestone

# ─── Template ────────────────────────────────────────────────────────────────
# Each entry: (order, title, description, week_offset_from_start)
# week_offset is the number of weeks after project start_date.
#
# Feel free to edit titles / descriptions / offsets here — the signal picks
# them up automatically.

MILESTONE_TEMPLATE = [
    (
        1,
        "Project Kickoff",
        (
            "Formal project initiation meeting. Confirm scope, stakeholders, "
            "communication plan, and high-level timeline with all parties."
        ),
        0,   # week 0 — same day as project start
    ),
    (
        2,
        "Requirements Sign-Off",
        (
            "Customer reviews and formally approves the full requirements "
            "specification document. Any open items are resolved before proceeding."
        ),
        2,   # week 2
    ),
    (
        3,
        "Design & Engineering Review",
        (
            "Internal design review covering mechanical, electrical, and software "
            "architecture. Customer receives the design pack for approval."
        ),
        4,   # week 4
    ),
    (
        4,
        "Manufacturing / Build Complete",
        (
            "All components are manufactured or procured and the robot/system "
            "build is physically complete in the workshop."
        ),
        8,   # week 8
    ),
    (
        5,
        "Factory Acceptance Test (FAT)",
        (
            "System is tested against the agreed acceptance criteria at the "
            "manufacturer's facility. Customer witnesses and signs off the FAT report."
        ),
        10,  # week 10
    ),
    (
        6,
        "Site Installation & Commissioning",
        (
            "Equipment is delivered, installed at the customer site, integrated "
            "with existing infrastructure, and commissioned to operational readiness."
        ),
        13,  # week 13
    ),
    (
        7,
        "Site Acceptance Test (SAT) & Final Sign-Off",
        (
            "Full system acceptance test performed on-site. Customer formally "
            "signs off the project as complete and transitions to support/warranty."
        ),
        15,  # week 15
    ),
]


# ─── Signal ───────────────────────────────────────────────────────────────────

@receiver(post_save, sender=Project)
def create_default_milestones(sender, instance: Project, created: bool, **kwargs):
    """
    Fires once — on Project *creation* only (not every save).
    Creates all 7 template milestones for the new project.
    If milestones already exist (e.g. fixture / import) we skip gracefully.
    """
    if not created:
        return

    # Avoid duplicates if someone calls Project.save() twice on a new instance
    if instance.milestones.exists():
        return

    # Base date: prefer project start_date, fall back to today
    base_date = instance.start_date or timezone.now().date()

    milestones = [
        Milestone(
            project=instance,
            order=order,
            title=title,
            description=description,
            status=Milestone.Status.PENDING,
            planned_date=base_date + timedelta(weeks=week_offset),
        )
        for order, title, description, week_offset in MILESTONE_TEMPLATE
    ]

    Milestone.objects.bulk_create(milestones)