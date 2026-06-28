from django.urls import path

from workspaces.views import (
    WorkspaceInvitationAcceptView,
    WorkspaceInvitationListCreateView,
    WorkspaceMemberDetailView,
    WorkspaceMemberListView,
)

urlpatterns = [
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
