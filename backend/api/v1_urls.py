from django.urls import path, include

urlpatterns = [
    path('auth/',          include('accounts.urls')),
    path('projects/',      include('projects.urls')),
    path('milestones/',    include('milestones.urls')),
    path('documents/',     include('documents.urls')),
    path('tickets/',       include('tickets.urls')),
    path('notifications/', include('notifications.urls')),
]