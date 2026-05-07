from rest_framework import serializers
# from .models import ChatRoom, ChatMessage, ChatReadReceipt   ← uncomment when in its own file
 
 
class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_role = serializers.SerializerMethodField()
 
    class Meta:
        model  = ChatMessage
        fields = ['id', 'sender_name', 'sender_role', 'message', 'created_at']
        read_only_fields = ['id', 'sender_name', 'sender_role', 'created_at']
 
    def get_sender_name(self, obj):
        if obj.sender:
            return obj.sender.full_name or obj.sender.email
        return "System"
 
    def get_sender_role(self, obj):
        return obj.sender.role if obj.sender else ""
 
 
class ChatRoomSerializer(serializers.ModelSerializer):
    """Lightweight room list item."""
    project_name  = serializers.CharField(source='project.name', read_only=True)
    unread_count  = serializers.SerializerMethodField()
    last_message  = serializers.SerializerMethodField()
    last_at       = serializers.SerializerMethodField()
 
    class Meta:
        model  = ChatRoom
        fields = ['id', 'project_name', 'unread_count', 'last_message', 'last_at']
 
    def _last_msg(self, obj):
        return obj.messages.last()
 
    def get_unread_count(self, obj):
        user    = self.context['request'].user
        receipt = obj.read_receipts.filter(user=user).first()
        if receipt:
            return obj.messages.filter(created_at__gt=receipt.last_read_at).exclude(sender=user).count()
        return obj.messages.exclude(sender=user).count()
 
    def get_last_message(self, obj):
        msg = self._last_msg(obj)
        return msg.message[:60] if msg else None
 
    def get_last_at(self, obj):
        msg = self._last_msg(obj)
        return msg.created_at.isoformat() if msg else None
 