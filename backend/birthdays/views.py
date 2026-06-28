from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from birthdays.models import Contact
from birthdays.serializers import ContactSerializer, ContactWriteSerializer
from birthdays.services import birthday_in_month, days_until_birthday, next_birthday
from workspaces.services import get_user_workspace


class WorkspaceMixin:
    def get_workspace(self):
        workspace = get_user_workspace(self.request.user)
        if workspace is None:
            raise NotFound("Workspace not found.")
        return workspace

    def get_contact_queryset(self):
        return Contact.objects.filter(workspace=self.get_workspace()).select_related(
            "birthday"
        )


class ContactListCreateView(WorkspaceMixin, APIView):
    def get(self, request):
        contacts = self.get_contact_queryset()
        return Response(ContactSerializer(contacts, many=True).data)

    def post(self, request):
        serializer = ContactWriteSerializer(
            data=request.data,
            context={"workspace": self.get_workspace()},
        )
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()
        return Response(
            ContactSerializer(contact).data,
            status=status.HTTP_201_CREATED,
        )


class ContactDetailView(WorkspaceMixin, APIView):
    def get_contact(self, contact_id):
        return get_object_or_404(self.get_contact_queryset(), pk=contact_id)

    def get(self, request, contact_id):
        contact = self.get_contact(contact_id)
        return Response(ContactSerializer(contact).data)

    def patch(self, request, contact_id):
        contact = self.get_contact(contact_id)
        serializer = ContactWriteSerializer(
            contact,
            data=request.data,
            partial=True,
            context={"workspace": self.get_workspace()},
        )
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()
        return Response(ContactSerializer(contact).data)

    def delete(self, request, contact_id):
        contact = self.get_contact(contact_id)
        contact.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BirthdayCalendarView(WorkspaceMixin, APIView):
    def get(self, request):
        try:
            year = int(request.query_params.get("year", date.today().year))
            month = int(request.query_params.get("month", date.today().month))
        except (TypeError, ValueError):
            return Response(
                {"detail": "Invalid year or month."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        events = []
        for contact in self.get_contact_queryset():
            occurrence = birthday_in_month(contact.birthday.birth_date, year, month)
            if occurrence is None:
                continue
            events.append(
                {
                    "id": contact.id,
                    "title": f"{contact.name} — ДР",
                    "start": occurrence.isoformat(),
                    "allDay": True,
                    "extendedProps": {
                        "contact_id": contact.id,
                        "relation": contact.relation,
                        "name": contact.name,
                    },
                }
            )
        return Response(events)


class UpcomingBirthdaysView(WorkspaceMixin, APIView):
    def get(self, request):
        limit = int(request.query_params.get("limit", 5))
        today = date.today()
        upcoming = []

        for contact in self.get_contact_queryset():
            birth_date = contact.birthday.birth_date
            next_date = next_birthday(birth_date, today)
            upcoming.append(
                {
                    "contact_id": contact.id,
                    "name": contact.name,
                    "relation": contact.relation,
                    "birth_date": birth_date.isoformat(),
                    "next_date": next_date.isoformat(),
                    "days_until": days_until_birthday(birth_date, today),
                }
            )

        upcoming.sort(key=lambda item: item["days_until"])
        return Response(upcoming[:limit])
