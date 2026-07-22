from django.urls import path

from crm import views

urlpatterns = [
    path("crm/organizations/", views.OrganizationListCreateView.as_view(), name="crm-orgs"),
    path(
        "crm/organizations/<int:org_id>/",
        views.OrganizationDetailView.as_view(),
        name="crm-org-detail",
    ),
    path("crm/people/", views.PersonListCreateView.as_view(), name="crm-people"),
    path(
        "crm/people/<int:person_id>/",
        views.PersonDetailView.as_view(),
        name="crm-person-detail",
    ),
    path("crm/activities/", views.ActivityListCreateView.as_view(), name="crm-activities"),
    path(
        "crm/activities/<int:activity_id>/",
        views.ActivityDetailView.as_view(),
        name="crm-activity-detail",
    ),
    path(
        "crm/projects/<int:project_id>/people/",
        views.ProjectPeopleView.as_view(),
        name="crm-project-people",
    ),
    path("crm/import-legacy/", views.CrmImportLegacyView.as_view(), name="crm-import-legacy"),
]
