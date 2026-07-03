from django.urls import path

from tracking.views import (
    CustomFieldDetailView,
    CustomFieldEnumerationDetailView,
    CustomFieldEnumerationListCreateView,
    CustomFieldListCreateView,
    IssueStatusDetailView,
    IssueStatusListCreateView,
    TrackerDetailView,
    TrackerListCreateView,
    TrackingMetadataView,
)

urlpatterns = [
    path("tracking/metadata/", TrackingMetadataView.as_view(), name="tracking-metadata"),
    path("tracking/trackers/", TrackerListCreateView.as_view(), name="tracker-list"),
    path(
        "tracking/trackers/<int:tracker_id>/",
        TrackerDetailView.as_view(),
        name="tracker-detail",
    ),
    path("tracking/statuses/", IssueStatusListCreateView.as_view(), name="status-list"),
    path(
        "tracking/statuses/<int:status_id>/",
        IssueStatusDetailView.as_view(),
        name="status-detail",
    ),
    path(
        "tracking/custom-fields/",
        CustomFieldListCreateView.as_view(),
        name="custom-field-list",
    ),
    path(
        "tracking/custom-fields/<int:field_id>/",
        CustomFieldDetailView.as_view(),
        name="custom-field-detail",
    ),
    path(
        "tracking/custom-fields/<int:field_id>/enumerations/",
        CustomFieldEnumerationListCreateView.as_view(),
        name="enumeration-list",
    ),
    path(
        "tracking/enumerations/<int:item_id>/",
        CustomFieldEnumerationDetailView.as_view(),
        name="enumeration-detail",
    ),
]
