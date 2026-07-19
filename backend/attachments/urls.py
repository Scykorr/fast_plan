from django.urls import path

from attachments.views import (
    AttachmentDetailView,
    CardAttachmentListCreateView,
    WBSAttachmentListCreateView,
)

urlpatterns = [
    path(
        "wbs/<int:wbs_id>/attachments/",
        WBSAttachmentListCreateView.as_view(),
        name="wbs-attachments",
    ),
    path(
        "cards/<int:card_id>/attachments/",
        CardAttachmentListCreateView.as_view(),
        name="card-attachments",
    ),
    path(
        "attachments/<int:attachment_id>/",
        AttachmentDetailView.as_view(),
        name="attachment-detail",
    ),
]
