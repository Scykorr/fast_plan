from django.urls import path

from workspaces.views import (
    WorkspaceActivateView,
    WorkspaceCapacityView,
    WorkspaceDashboardView,
    WorkspaceInvitationAcceptView,
    WorkspaceInvitationDetailView,
    WorkspaceInvitationListCreateView,
    WorkspaceListView,
    WorkspaceMemberDetailView,
    WorkspaceMemberListView,
    WorkspaceMyTasksView,
    WorkspaceSearchView,
)

urlpatterns = [
    path("workspaces/", WorkspaceListView.as_view(), name="workspace-list"),
    path(
        "workspaces/<int:workspace_id>/activate/",
        WorkspaceActivateView.as_view(),
        name="workspace-activate",
    ),
    path(
        "workspace/dashboard/",
        WorkspaceDashboardView.as_view(),
        name="workspace-dashboard",
    ),
    path(
        "workspace/search/",
        WorkspaceSearchView.as_view(),
        name="workspace-search",
    ),
    path(
        "workspace/my-tasks/",
        WorkspaceMyTasksView.as_view(),
        name="workspace-my-tasks",
    ),
    path(
        "workspace/capacity/",
        WorkspaceCapacityView.as_view(),
        name="workspace-capacity",
    ),
    path("workspace/members/", WorkspaceMemberListView.as_view(), name="workspace-members"),
    path(
        "workspace/members/<int:member_id>/",
        WorkspaceMemberDetailView.as_view(),
        name="workspace-member-detail",
    ),
    path(
        "workspace/invitations/",
        WorkspaceInvitationListCreateView.as_view(),
        name="workspace-invitations",
    ),
    path(
        "workspace/invitations/<int:invitation_id>/resend/",
        WorkspaceInvitationDetailView.as_view(),
        name="workspace-invitation-resend",
    ),
    path(
        "workspace/invitations/<int:invitation_id>/",
        WorkspaceInvitationDetailView.as_view(),
        name="workspace-invitation-detail",
    ),
    path(
        "workspace/invitations/<str:token>/accept/",
        WorkspaceInvitationAcceptView.as_view(),
        name="workspace-invitation-accept",
    ),
]
