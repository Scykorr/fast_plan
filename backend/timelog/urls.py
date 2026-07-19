from django.urls import path

from timelog.views import TimeEntryDetailView, TimeEntryListCreateView

urlpatterns = [
    path("workspace/time-entries/", TimeEntryListCreateView.as_view(), name="time-entry-list"),
    path(
        "workspace/time-entries/<int:entry_id>/",
        TimeEntryDetailView.as_view(),
        name="time-entry-detail",
    ),
]
