from django.urls import path

from attachments.views import (
    AttachmentDetailView,
    CardAttachmentListCreateView,
    ProcessWorkNodeAttachmentListCreateView,
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
        "process/work-nodes/<int:node_id>/attachments/",
        ProcessWorkNodeAttachmentListCreateView.as_view(),
        name="process-work-node-attachments",
    ),
    path(
        "attachments/<int:attachment_id>/",
        AttachmentDetailView.as_view(),
        name="attachment-detail",
    ),
]
