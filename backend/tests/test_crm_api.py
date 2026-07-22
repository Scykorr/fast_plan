"""P6a CRM foundation API tests."""

import pytest
from rest_framework import status

from birthdays.models import Birthday, Contact
from crm.models import Activity, Organization, Person, ProjectPersonLink
from projects.models import Project, Stakeholder


@pytest.mark.django_db
def test_organization_and_person_crud(authenticated_client, workspace):
    org = authenticated_client.post(
        "/api/crm/organizations/",
        {"name": "Acme LLC", "industry": "IT"},
        format="json",
    )
    assert org.status_code == status.HTTP_201_CREATED
    org_id = org.data["id"]

    person = authenticated_client.post(
        "/api/crm/people/",
        {
            "full_name": "Ada Lovelace",
            "email": "ada@acme.test",
            "organization_id": org_id,
            "organization_title": "CTO",
        },
        format="json",
    )
    assert person.status_code == status.HTTP_201_CREATED
    assert person.data["organizations"][0]["name"] == "Acme LLC"

    listed = authenticated_client.get("/api/crm/people/?q=Ada")
    assert listed.status_code == status.HTTP_200_OK
    assert len(listed.data) == 1


@pytest.mark.django_db
def test_activity_timeline(authenticated_client, workspace, user):
    person = Person.objects.create(workspace=workspace, full_name="Bob")
    created = authenticated_client.post(
        "/api/crm/activities/",
        {
            "kind": "call",
            "subject": "Discovery",
            "body": "Talked about scope",
            "person_id": person.id,
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["kind"] == "call"
    assert Activity.objects.filter(person=person).count() == 1

    listed = authenticated_client.get(f"/api/crm/activities/?person_id={person.id}")
    assert listed.status_code == status.HTTP_200_OK
    assert listed.data[0]["subject"] == "Discovery"


@pytest.mark.django_db
def test_project_client_org_and_stakeholder_person(
    authenticated_client, workspace, user
):
    org = Organization.objects.create(workspace=workspace, name="Client Co")
    project = Project.objects.create(
        workspace=workspace, name="CRM Proj", manager=user
    )
    patched = authenticated_client.patch(
        f"/api/projects/{project.id}/",
        {"client_organization_id": org.id},
        format="json",
    )
    assert patched.status_code == status.HTTP_200_OK
    assert patched.data["client_organization_id"] == org.id
    assert patched.data["client_organization_name"] == "Client Co"

    person = Person.objects.create(
        workspace=workspace, full_name="Carol", email="carol@client.test"
    )
    stake = authenticated_client.post(
        f"/api/projects/{project.id}/stakeholders/",
        {
            "name": "Carol",
            "role": "Sponsor",
            "interest": 5,
            "influence": 4,
            "contact_email": "carol@client.test",
            "person_id": person.id,
        },
        format="json",
    )
    assert stake.status_code == status.HTTP_201_CREATED
    assert stake.data["person_id"] == person.id


@pytest.mark.django_db
def test_import_legacy_contacts_and_stakeholders(
    authenticated_client, workspace, user
):
    contact = Contact.objects.create(
        workspace=workspace, name="Dave Birthday", relation="friend"
    )
    Birthday.objects.create(contact=contact, birth_date="1990-05-01")
    project = Project.objects.create(
        workspace=workspace, name="Legacy Proj", manager=user
    )
    Stakeholder.objects.create(
        project=project,
        name="Eve Stake",
        role="Owner",
        contact_email="eve@example.com",
        interest=4,
        influence=5,
    )

    imported = authenticated_client.post("/api/crm/import-legacy/", {}, format="json")
    assert imported.status_code == status.HTTP_200_OK
    assert imported.data["imported_contacts"] >= 1
    assert imported.data["imported_stakeholders"] >= 1
    assert Person.objects.filter(full_name="Dave Birthday").exists()
    assert Person.objects.filter(email="eve@example.com").exists()
    assert ProjectPersonLink.objects.filter(project=project).exists()
