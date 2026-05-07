from django.contrib import admin
# from .models import ChatRoom, ChatMessage, ChatReadReceipt
 
 
class ChatMessageInline(admin.TabularInline):
    model           = ChatMessage
    extra           = 0
    fields          = ['sender', 'message', 'created_at']
    readonly_fields = ['created_at']
 
 
# @admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['project', 'created_at']
    inlines      = [ChatMessageInline]
 
 
# @admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display  = ['room', 'sender', 'message', 'created_at']
    search_fields = ['message', 'sender__email']
    readonly_fields = ['created_at']
 