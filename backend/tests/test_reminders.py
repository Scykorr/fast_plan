from datetime import date, timedelta

import pytest
from django.core.management import call_command

from birthdays.models import Birthday, Contact
from kanban.models import Card
from notifications.models import Notification
from notifications.services import run_all_reminders
from projects.models import ScheduleActivity, WBSNode
from tests.factories import ProjectFactory


@pytest.mark.django_db
def test_send_reminders_creates_birthday_and_deadline(workspace, user):
    contact = Contact.objects.create(workspace=workspace, name="Ada", relation="друг")
    Birthday.objects.create(
        contact=contact,
        birth_date=date.today().replace(year=1990),
    )
    project = ProjectFactory(
        workspace=workspace,
        manager=user,
        end_date=date.today() + timedelta(days=3),
    )
    root = project.wbs_nodes.filter(parent__isnull=True).first()
    node = WBSNode.objects.create(
        project=project,
        parent=root,
        title="WP due",
        code="1.1",
        node_type=WBSNode.NodeType.WORK_PACKAGE,
        position=0,
    )
    ScheduleActivity.objects.create(
        wbs_node=node,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=2),
        progress=10,
        is_milestone=False,
    )
    board = workspace.boards.first()
    column = board.columns.first()
    Card.objects.create(
        column=column,
        title="Card due",
        position=0,
        due_date=date.today() + timedelta(days=1),
    )

    stats = run_all_reminders(today=date.today())
    assert stats["birthdays"] >= 1
    assert stats["deadlines"] >= 2
    assert Notification.objects.filter(
        notification_type=Notification.NotificationType.BIRTHDAY
    ).exists()
    assert Notification.objects.filter(
        notification_type=Notification.NotificationType.DEADLINE
    ).exists()


@pytest.mark.django_db
def test_send_reminders_is_idempotent(workspace, user):
    contact = Contact.objects.create(workspace=workspace, name="Bob", relation="коллега")
    Birthday.objects.create(
        contact=contact,
        birth_date=date.today().replace(year=1988),
    )
    first = run_all_reminders(today=date.today())
    second = run_all_reminders(today=date.today())
    assert first["birthdays"] >= 1
    assert second["birthdays"] == 0
    assert (
        Notification.objects.filter(
            user=user, notification_type=Notification.NotificationType.BIRTHDAY
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_send_reminders_sends_digest_email(workspace, user, settings, mailoutbox):
    from django.core.cache import cache

    cache.clear()
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.FRONTEND_BASE_URL = "http://frontend.test"
    contact = Contact.objects.create(workspace=workspace, name="Eve", relation="друг")
    Birthday.objects.create(
        contact=contact,
        birth_date=date.today().replace(year=1991),
    )
    stats = run_all_reminders(today=date.today())
    assert stats["emails"] >= 1
    assert len(mailoutbox) >= 1
    assert "ДР: Eve" in mailoutbox[0].body


@pytest.mark.django_db
def test_send_reminders_management_command(workspace, user, capsys):
    contact = Contact.objects.create(workspace=workspace, name="Cara", relation="друг")
    Birthday.objects.create(
        contact=contact,
        birth_date=date.today().replace(year=1995),
    )
    call_command("send_reminders")
    captured = capsys.readouterr()
    assert "birthdays=" in captured.out
    assert Notification.objects.filter(
        notification_type=Notification.NotificationType.BIRTHDAY
    ).exists()
