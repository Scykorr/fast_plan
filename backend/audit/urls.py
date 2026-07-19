from django.urls import path

from audit.views import AuditLogListView

urlpatterns = [
    path("workspace/audit/", AuditLogListView.as_view(), name="workspace-audit"),
]
