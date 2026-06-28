import factory
from datetime import date
from django.contrib.auth import get_user_model

from birthdays.models import Birthday, Contact
from kanban.models import Board, Card, Column
from projects.models import Project
from workspaces.models import Workspace, WorkspaceMember

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    first_name = "Test"
    last_name = "User"

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted or "testpass123"
        self.set_password(password)
        if create:
            self.save()


class WorkspaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Workspace

    name = "Test Workspace"
    owner = factory.SubFactory(UserFactory)


class WorkspaceMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkspaceMember

    workspace = factory.SubFactory(WorkspaceFactory)
    user = factory.SubFactory(UserFactory)
    role = WorkspaceMember.Role.OWNER


class BoardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Board

    workspace = factory.SubFactory(WorkspaceFactory)
    title = "Test Board"
    position = 0


class ColumnFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Column

    board = factory.SubFactory(BoardFactory)
    title = "To Do"
    position = 0


class CardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Card

    column = factory.SubFactory(ColumnFactory)
    title = "Test Card"
    description = ""
    position = 0


class ContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contact

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda n: f"Contact {n}")
    relation = "друг"

    @factory.post_generation
    def birthday(self, create, extracted, **kwargs):
        if not create:
            return
        Birthday.objects.create(
            contact=self,
            birth_date=extracted if extracted is not None else date(1995, 6, 15),
        )


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda n: f"Project {n}")
    description = "Test project"
    manager = factory.SubFactory(UserFactory)
