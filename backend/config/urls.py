from django.contrib import admin
from django.urls import include, path

from config.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("kanban.urls")),
    path("api/", include("birthdays.urls")),
    path("api/", include("projects.urls")),
    path("api/", include("finance.urls")),
    path("api/", include("workspaces.urls")),
    path("api/", include("notifications.urls")),
    path("api/", include("tracking.urls")),
]
