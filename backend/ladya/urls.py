from django.urls import path

from ladya import views

urlpatterns = [
    path("ladya/settings/", views.LadyaSettingsView.as_view(), name="ladya-settings"),
    path(
        "ladya/laboratories/",
        views.LaboratoryListCreateView.as_view(),
        name="ladya-lab-list",
    ),
    path(
        "ladya/laboratories/<int:lab_id>/",
        views.LaboratoryDetailView.as_view(),
        name="ladya-lab-detail",
    ),
    path(
        "ladya/packages/",
        views.PackageListCreateView.as_view(),
        name="ladya-package-list",
    ),
    path(
        "ladya/packages/<int:package_id>/",
        views.PackageDetailView.as_view(),
        name="ladya-package-detail",
    ),
    path(
        "ladya/packages/<int:package_id>/transition/",
        views.PackageTransitionView.as_view(),
        name="ladya-package-transition",
    ),
    path(
        "ladya/packages/<int:package_id>/files/",
        views.PackageFileUploadView.as_view(),
        name="ladya-package-files",
    ),
    path(
        "ladya/intake/",
        views.IntakeListCreateView.as_view(),
        name="ladya-intake-list",
    ),
    path(
        "ladya/intake/<int:intake_id>/triage/",
        views.IntakeTriageView.as_view(),
        name="ladya-intake-triage",
    ),
    path(
        "ladya/intake/<int:intake_id>/convert/",
        views.IntakeConvertView.as_view(),
        name="ladya-intake-convert",
    ),
]
