"""
Auto-create a ChatRoom whenever a Project is created.
Add to chat/apps.py:  default_auto_field + ready() → signals import
"""
 
from django.db.models.signals import post_save
from django.dispatch import receiver
# from projects.models import Project
# from .models import ChatRoom
 
# @receiver(post_save, sender=Project)
def create_chat_room_for_project(sender, instance, created, **kwargs):
    if created:
        ChatRoom.objects.get_or_create(project=instance)
 