from django.urls import path

from crm import deals_views, views

urlpatterns = [
    path("crm/organizations/", views.OrganizationListCreateView.as_view(), name="crm-orgs"),
    path(
        "crm/organizations/<int:org_id>/",
        views.OrganizationDetailView.as_view(),
        name="crm-org-detail",
    ),
    path(
        "crm/organizations/<int:org_id>/tags/",
        views.OrganizationTagView.as_view(),
        name="crm-org-tags",
    ),
    path(
        "crm/organizations/<int:org_id>/tags/<int:tag_id>/",
        views.OrganizationTagView.as_view(),
        name="crm-org-tag-detail",
    ),
    path("crm/people/", views.PersonListCreateView.as_view(), name="crm-people"),
    path(
        "crm/people/<int:person_id>/",
        views.PersonDetailView.as_view(),
        name="crm-person-detail",
    ),
    path(
        "crm/people/<int:person_id>/tags/",
        views.PersonTagView.as_view(),
        name="crm-person-tags",
    ),
    path(
        "crm/people/<int:person_id>/tags/<int:tag_id>/",
        views.PersonTagView.as_view(),
        name="crm-person-tag-detail",
    ),
    path("crm/activities/", views.ActivityListCreateView.as_view(), name="crm-activities"),
    path(
        "crm/activities/<int:activity_id>/",
        views.ActivityDetailView.as_view(),
        name="crm-activity-detail",
    ),
    path("crm/tags/", views.TagListCreateView.as_view(), name="crm-tags"),
    path(
        "crm/tags/<int:tag_id>/",
        views.TagDetailView.as_view(),
        name="crm-tag-detail",
    ),
    path("crm/segments/", views.SegmentListCreateView.as_view(), name="crm-segments"),
    path(
        "crm/segments/<int:segment_id>/",
        views.SegmentDetailView.as_view(),
        name="crm-segment-detail",
    ),
    path(
        "crm/segments/<int:segment_id>/members/",
        views.SegmentMembersView.as_view(),
        name="crm-segment-members",
    ),
    path("crm/comments/", views.CommentListCreateView.as_view(), name="crm-comments"),
    path(
        "crm/comments/<int:comment_id>/",
        views.CommentDetailView.as_view(),
        name="crm-comment-detail",
    ),
    path(
        "crm/attachments/",
        views.AttachmentListCreateView.as_view(),
        name="crm-attachments",
    ),
    path(
        "crm/attachments/<int:attachment_id>/",
        views.AttachmentDetailView.as_view(),
        name="crm-attachment-detail",
    ),
    path(
        "crm/projects/<int:project_id>/people/",
        views.ProjectPeopleView.as_view(),
        name="crm-project-people",
    ),
    path("crm/import-legacy/", views.CrmImportLegacyView.as_view(), name="crm-import-legacy"),
    path("crm/pipeline/", deals_views.PipelineBoardView.as_view(), name="crm-pipeline"),
    path("crm/deals/", deals_views.DealListCreateView.as_view(), name="crm-deals"),
    path(
        "crm/deals/forecast/",
        deals_views.DealForecastView.as_view(),
        name="crm-deals-forecast",
    ),
    path(
        "crm/deals/<int:deal_id>/",
        deals_views.DealDetailView.as_view(),
        name="crm-deal-detail",
    ),
    path(
        "crm/deals/<int:deal_id>/move/",
        deals_views.DealMoveView.as_view(),
        name="crm-deal-move",
    ),
    path(
        "crm/deals/<int:deal_id>/tasks/",
        deals_views.DealTaskListCreateView.as_view(),
        name="crm-deal-tasks",
    ),
    path(
        "crm/deals/<int:deal_id>/tasks/<int:task_id>/",
        deals_views.DealTaskDetailView.as_view(),
        name="crm-deal-task-detail",
    ),
]
