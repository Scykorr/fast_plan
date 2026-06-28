from django.urls import path

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
        "calendar/milestones/",
        WorkspaceMilestonesCalendarView.as_view(),
        name="workspace-milestones-calendar",
    ),
    path("wbs/<int:wbs_id>/", WBSNodeDetailView.as_view(), name="wbs-detail"),
    path(
        "activities/<int:activity_id>/",
        ScheduleActivityDetailView.as_view(),
        name="activity-detail",
    ),
]
