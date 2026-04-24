from django.urls import path
from .views import (
    NotificationListView,
    NotificationUnreadCountView,
    NotificationMarkReadView,
    NotificationMarkSingleReadView,
    NotificationDeleteView,
    ActivityLogListView,
    ProjectActivityLogView,
)

urlpatterns = [
    # Notification list
    path('',                            NotificationListView.as_view(),         name='notification-list'),

    # Bell icon count
    path('unread-count/',               NotificationUnreadCountView.as_view(),  name='notification-unread-count'),

    # Bulk mark read
    path('mark-read/',                  NotificationMarkReadView.as_view(),     name='notification-mark-read'),

    # Single notification actions
    path('<int:pk>/read/',              NotificationMarkSingleReadView.as_view(), name='notification-read'),
    path('<int:pk>/',                   NotificationDeleteView.as_view(),       name='notification-delete'),

    # Activity feed — global
    path('activity/',                   ActivityLogListView.as_view(),          name='activity-log'),

    # Activity feed — per project
    path('activity/project/<int:project_pk>/', ProjectActivityLogView.as_view(), name='project-activity'),
]