from django.urls import path

from birthdays.views import (
    BirthdayCalendarView,
    ContactDetailView,
    ContactListCreateView,
    UpcomingBirthdaysView,
)

urlpatterns = [
    path("contacts/", ContactListCreateView.as_view(), name="contact-list"),
    path("contacts/<int:contact_id>/", ContactDetailView.as_view(), name="contact-detail"),
    path("calendar/birthdays/", BirthdayCalendarView.as_view(), name="birthday-calendar"),
    path("calendar/upcoming/", UpcomingBirthdaysView.as_view(), name="birthday-upcoming"),
]
