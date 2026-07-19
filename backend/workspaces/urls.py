from django.urls import path

from workspaces.views import (
    WorkspaceActivateView,
    WorkspaceInvitationAcceptView,
    WorkspaceInvitationListCreateView,
    WorkspaceListView,
    WorkspaceMemberDetailView,
    WorkspaceMemberListView,
)

urlpatterns = [
    path("workspaces/", WorkspaceListView.as_view(), name="workspace-list"),
    path(
        "workspaces/<int:workspace_id>/activate/",
        WorkspaceActivateView.as_view(),
        name="workspace-activate",
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
        "workspace/invitations/<str:token>/accept/",
        WorkspaceInvitationAcceptView.as_view(),
        name="workspace-invitation-accept",
    ),
]
