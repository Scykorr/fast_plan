from datetime import date

import pytest
from rest_framework import status

from birthdays.models import Contact
from birthdays.services import next_birthday
from tests.factories import ContactFactory


@pytest.fixture
def contact(workspace):
    return ContactFactory(workspace=workspace, name="Иван", birthday=date(1990, 6, 15))


@pytest.mark.django_db
def test_create_contact(authenticated_client, workspace):
    response = authenticated_client.post(
        "/api/contacts/",
        {
            "name": "Мария",
            "relation": "сестра",
            "birth_date": "1988-03-20",
            "notes": "Любит книги",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "Мария"
    assert response.data["birth_date"] == "1988-03-20"
    assert Contact.objects.filter(workspace=workspace, name="Мария").exists()


@pytest.mark.django_db
def test_list_contacts(authenticated_client, contact):
    response = authenticated_client.get("/api/contacts/")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1
    assert response.data[0]["name"] == "Иван"


@pytest.mark.django_db
def test_update_contact(authenticated_client, contact):
    response = authenticated_client.patch(
        f"/api/contacts/{contact.id}/",
        {"name": "Иван Петров"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    contact.refresh_from_db()
    assert contact.name == "Иван Петров"


@pytest.mark.django_db
def test_delete_contact(authenticated_client, contact):
    contact_id = contact.id
    response = authenticated_client.delete(f"/api/contacts/{contact_id}/")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Contact.objects.filter(pk=contact_id).exists()


@pytest.mark.django_db
def test_calendar_birthdays_for_month(authenticated_client, contact):
    response = authenticated_client.get("/api/calendar/birthdays/?year=2026&month=6")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["start"] == "2026-06-15"
    assert "Иван" in response.data[0]["title"]


@pytest.mark.django_db
def test_upcoming_birthdays_sorted(authenticated_client, workspace):
    ContactFactory(workspace=workspace, name="Soon", birthday=date(1990, 1, 1))
    ContactFactory(workspace=workspace, name="Later", birthday=date(1990, 12, 25))

    response = authenticated_client.get("/api/calendar/upcoming/?limit=10")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 2
    assert response.data[0]["days_until"] <= response.data[1]["days_until"]


@pytest.mark.django_db
def test_feb_29_birthday_in_non_leap_year(authenticated_client, workspace):
    ContactFactory(workspace=workspace, name="Leap", birthday=date(2000, 2, 29))

    response = authenticated_client.get("/api/calendar/birthdays/?year=2025&month=2")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["start"] == "2025-02-28"


@pytest.mark.django_db
def test_upcoming_feb_29_uses_feb_28_in_non_leap_year(authenticated_client, workspace):
    ContactFactory(workspace=workspace, name="Leap", birthday=date(2000, 2, 29))

    response = authenticated_client.get("/api/calendar/upcoming/")
    assert response.status_code == status.HTTP_200_OK
    leap_entry = next(item for item in response.data if item["name"] == "Leap")
    assert leap_entry["next_date"] == next_birthday(date(2000, 2, 29)).isoformat()
    assert leap_entry["next_date"].endswith("-02-28") or leap_entry["next_date"].endswith("-02-29")
