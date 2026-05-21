from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from milestones.urls import subtask_detail_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.v1_urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/auth/',          include('accounts.urls')),
    path('api/v1/milestones/',    include('milestones.urls')),
    path('api/v1/subtasks/',      include(subtask_detail_urlpatterns)),
    path('api/v1/documents/',     include('documents.urls')),
    path('api/v1/tickets/',       include('tickets.urls')),
    path('api/v1/notifications/', include('notifications.urls')),

    # company_master mounted at /api/v1/company/ keeps existing routes intact:
    #   /api/v1/company/companies/
    #   /api/v1/company/customers/
    path('api/v1/company/', include('company_master.urls')),

    # Direct /api/v1/ prefix so the frontend can call:
    #   GET /api/v1/companies/
    #   GET /api/v1/customers/?company_id=1
    path('api/v1/', include('company_master.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)