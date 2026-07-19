from django.urls import path

from projects.comment_views import (
    CardCommentListCreateView,
    WBSCommentListCreateView,
    WorkItemCommentDetailView,
)
from projects.pmbok_views import (
    BaselineDetailView,
    BaselineListCreateView,
    CriticalPathView,
    ProjectCharterView,
    ProjectExportView,
    RACIDetailView,
    RACIListCreateView,
    RiskDetailView,
    RiskListCreateView,
    StakeholderDetailView,
    StakeholderListCreateView,
)
from projects.views import (
    ActivityDependencyCreateView,
    ProjectCalendarView,
    ProjectDashboardView,
    ProjectDetailView,
    ProjectListCreateView,
    ProjectScheduleView,
    ScheduleActivityDetailView,
    WBSNodeDetailView,
    WBSTreeView,
    WorkspaceMilestonesCalendarView,
)

urlpatterns = [
    path("projects/", ProjectListCreateView.as_view(), name="project-list"),
    path("projects/<int:project_id>/", ProjectDetailView.as_view(), name="project-detail"),
    path(
        "projects/<int:project_id>/dashboard/",
        ProjectDashboardView.as_view(),
        name="project-dashboard",
    ),
    path("projects/<int:project_id>/wbs/", WBSTreeView.as_view(), name="project-wbs"),
    path(
        "projects/<int:project_id>/schedule/",
        ProjectScheduleView.as_view(),
        name="project-schedule",
    ),
    path(
        "projects/<int:project_id>/dependencies/",
        ActivityDependencyCreateView.as_view(),
        name="project-dependencies",
    ),
    path(
        "projects/<int:project_id>/calendar/",
        ProjectCalendarView.as_view(),
        name="project-calendar",
    ),
    path(
        "projects/<int:project_id>/critical-path/",
        CriticalPathView.as_view(),
        name="project-critical-path",
    ),
    path(
        "projects/<int:project_id>/export/",
        ProjectExportView.as_view(),
        name="project-export",
    ),
    path(
        "projects/<int:project_id>/risks/",
        RiskListCreateView.as_view(),
        name="project-risks",
    ),
    path("risks/<int:risk_id>/", RiskDetailView.as_view(), name="risk-detail"),
    path(
        "projects/<int:project_id>/stakeholders/",
        StakeholderListCreateView.as_view(),
        name="project-stakeholders",
    ),
    path(
        "stakeholders/<int:stakeholder_id>/",
        StakeholderDetailView.as_view(),
        name="stakeholder-detail",
    ),
    path(
        "projects/<int:project_id>/charter/",
        ProjectCharterView.as_view(),
        name="project-charter",
    ),
    path(
        "projects/<int:project_id>/raci/",
        RACIListCreateView.as_view(),
        name="project-raci",
    ),
    path("raci/<int:raci_id>/", RACIDetailView.as_view(), name="raci-detail"),
    path(
        "projects/<int:project_id>/baselines/",
        BaselineListCreateView.as_view(),
        name="project-baselines",
    ),
    path(
        "baselines/<int:baseline_id>/",
        BaselineDetailView.as_view(),
        name="baseline-detail",
    ),
    path(
        "calendar/milestones/",
        WorkspaceMilestonesCalendarView.as_view(),
        name="workspace-milestones-calendar",
    ),
    path("wbs/<int:wbs_id>/", WBSNodeDetailView.as_view(), name="wbs-detail"),
    path(
        "wbs/<int:wbs_id>/comments/",
        WBSCommentListCreateView.as_view(),
        name="wbs-comments",
    ),
    path(
        "cards/<int:card_id>/comments/",
        CardCommentListCreateView.as_view(),
        name="card-comments",
    ),
    path(
        "comments/<int:comment_id>/",
        WorkItemCommentDetailView.as_view(),
        name="comment-detail",
    ),
    path(
        "activities/<int:activity_id>/",
        ScheduleActivityDetailView.as_view(),
        name="activity-detail",
    ),
]
