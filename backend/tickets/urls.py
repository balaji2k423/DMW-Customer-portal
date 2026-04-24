from django.urls import path
from .views import (
    TicketListCreateView,
    TicketDetailView,
    TicketStatusChangeView,
    TicketCommentListCreateView,
    TicketCommentDetailView,
    TicketAttachmentUploadView,
    TicketAttachmentDeleteView,
    TicketStatusHistoryView,
    TicketSummaryView,
)

urlpatterns = [
    # Summary stats for dashboard
    path('summary/',                                        TicketSummaryView.as_view(),            name='ticket-summary'),

    # Tickets CRUD
    path('',                                                TicketListCreateView.as_view(),         name='ticket-list'),
    path('<int:pk>/',                                       TicketDetailView.as_view(),             name='ticket-detail'),

    # Status change with note
    path('<int:pk>/status/',                                TicketStatusChangeView.as_view(),       name='ticket-status'),

    # Comment thread
    path('<int:ticket_pk>/comments/',                       TicketCommentListCreateView.as_view(),  name='ticket-comments'),
    path('<int:ticket_pk>/comments/<int:pk>/',              TicketCommentDetailView.as_view(),      name='ticket-comment-detail'),

    # Attachments
    path('<int:ticket_pk>/attachments/',                    TicketAttachmentUploadView.as_view(),   name='ticket-attachments'),
    path('<int:ticket_pk>/attachments/<int:pk>/',           TicketAttachmentDeleteView.as_view(),   name='ticket-attachment-delete'),

    # Audit trail
    path('<int:ticket_pk>/history/',                        TicketStatusHistoryView.as_view(),      name='ticket-history'),
]