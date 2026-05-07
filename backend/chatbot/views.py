from django.utils import timezone
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
# from projects.models import ProjectMember
# from .models import ChatRoom, ChatMessage, ChatReadReceipt
# from .serializers import ChatRoomSerializer, ChatMessageSerializer
# from api.throttling import BurstRateThrottle, SustainedRateThrottle
 
 
def _get_accessible_rooms(user):
    """Returns ChatRoom queryset the user may access."""
    if user.role in ('project_manager', 'admin'):
        return ChatRoom.objects.select_related('project').all()
    project_ids = ProjectMember.objects.filter(user=user).values_list('project_id', flat=True)
    return ChatRoom.objects.filter(project_id__in=project_ids).select_related('project')
 
 
class ChatRoomListView(generics.ListAPIView):
    """
    GET /api/chat/rooms/
    Returns rooms the logged-in user can access, enriched with
    unread count and last message snippet.
    """
    serializer_class   = ChatRoomSerializer
    permission_classes = [IsAuthenticated]
    # throttle_classes   = [BurstRateThrottle]
    pagination_class   = None
 
    def get_queryset(self):
        return _get_accessible_rooms(self.request.user)
 
 
class ChatMessageListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/chat/rooms/<room_id>/messages/  → full message thread
    POST /api/chat/rooms/<room_id>/messages/  → send a message
    """
    serializer_class   = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    # throttle_classes   = [BurstRateThrottle, SustainedRateThrottle]
 
    def get_queryset(self):
        room = self._get_room()
        return ChatMessage.objects.filter(room=room).select_related('sender')
 
    def _get_room(self):
        room_id = self.kwargs['room_id']
        rooms   = _get_accessible_rooms(self.request.user)
        try:
            return rooms.get(pk=room_id)
        except ChatRoom.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have access to this chat room.")
 
    def perform_create(self, serializer):
        room   = self._get_room()
        sender = self.request.user
        msg    = serializer.save(room=room, sender=sender)
 
        # Fire ticket_commented-style notification to other project members
        try:
            from notifications.models import Notification
            from projects.models import ProjectMember as PM
 
            members = PM.objects.filter(
                project=room.project
            ).exclude(user=sender).select_related('user')
 
            for membership in members:
                Notification.objects.create(
                    recipient   = membership.user,
                    actor       = sender,
                    type        = Notification.Type.TICKET_COMMENTED,
                    title       = f"New message in {room.project.name}",
                    message     = msg.message[:200],
                    project_id  = room.project_id,
                )
        except Exception:
            pass  # non-fatal
 
 
class ChatMarkReadView(APIView):
    """
    POST /api/chat/rooms/<room_id>/read/
    Updates the caller's read-receipt for this room.
    """
    permission_classes = [IsAuthenticated]
 
    def post(self, request, room_id):
        rooms = _get_accessible_rooms(request.user)
        try:
            room = rooms.get(pk=room_id)
        except ChatRoom.DoesNotExist:
            return Response({'error': 'Room not found.'}, status=status.HTTP_404_NOT_FOUND)
 
        ChatReadReceipt.objects.update_or_create(
            room=room, user=request.user,
            defaults={'last_read_at': timezone.now()},
        )
        return Response({'status': 'ok'})