"""
A ChatRoom is auto-created for every Project.
Members of that project (and project managers) can post messages.
Unread tracking: last_read_at per user.
"""
 
from django.db import models
from django.conf import settings
 
 
class ChatRoom(models.Model):
    """One chat room per project."""
    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='chat_room',
    )
    created_at = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f"ChatRoom for {self.project.name}"
 
 
class ChatMessage(models.Model):
    room       = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chat_messages',
    )
    message    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['created_at']
 
    def __str__(self):
        return f"[{self.room.project.name}] {self.sender}: {self.message[:40]}"
 
 
class ChatReadReceipt(models.Model):
    """Tracks last-read position per user per room."""
    room         = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='read_receipts')
    user         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_read_receipts',
    )
    last_read_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        unique_together = ('room', 'user')
 