"""
Include in your project urls.py:
    path('api/chat/', include('chat.urls')),
"""
 
from django.urls import path
# from .views import ChatRoomListView, ChatMessageListCreateView, ChatMarkReadView
 
urlpatterns_chat = [
    path('rooms/',                               ChatRoomListView.as_view(),            name='chat-room-list'),
    path('rooms/<int:room_id>/messages/',        ChatMessageListCreateView.as_view(),   name='chat-messages'),
    path('rooms/<int:room_id>/read/',            ChatMarkReadView.as_view(),            name='chat-mark-read'),
]
 