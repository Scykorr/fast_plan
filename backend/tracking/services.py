from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from tracking.models import (
    CustomField,
    CustomFieldEnumeration,
    CustomFieldTracker,
    CustomValue,
    IssueStatus,
    Tracker,
)

DEFAULT_TRACKERS = (
    ("Проект", Tracker.Target.PROJECT, True),
    ("Задача", Tracker.Target.ISSUE, True),
    ("Веха", Tracker.Target.ISSUE, False),
)

DEFAULT_STATUSES = (
    ("Новая", False, True),
    ("В работе", False, False),
    ("Решена", False, False),
    ("Закрыта", True, False),
)


@transaction.atomic
def seed_workspace_tracking(workspace) -> None:
    if Tracker.objects.filter(workspace=workspace).exists():
        return

    trackers = []
    for index, (name, target, is_default) in enumerate(DEFAULT_TRACKERS):
        trackers.append(
            Tracker.objects.create(
                workspace=workspace,
                name=name,
                target=target,
                position=index,
                is_default=is_default,
            )
        )

    for index, (name, is_closed, is_default) in enumerate(DEFAULT_STATUSES):
        IssueStatus.objects.create(
            workspace=workspace,
            name=name,
            position=index,
            is_closed=is_closed,
            is_default=is_default,
        )

    project_tracker = next(t for t in trackers if t.target == Tracker.Target.PROJECT)
    issue_tracker = next(t for t in trackers if t.name == "Задача")

    priority_field = CustomField.objects.create(
        workspace=workspace,
        name="Приоритет",
        field_format=CustomField.FieldFormat.LIST,
        position=0,
    )
    for pos, label in enumerate(("Низкий", "Нормальный", "Высокий", "Срочный")):
        CustomFieldEnumeration.objects.create(
            custom_field=priority_field,
            name=label,
            position=pos,
        )
    CustomFieldTracker.objects.create(custom_field=priority_field, tracker=issue_tracker)

    effort_field = CustomField.objects.create(
        workspace=workspace,
        name="Оценка (ч)",
        field_format=CustomField.FieldFormat.FLOAT,
        position=1,
    )
    CustomFieldTracker.objects.create(custom_field=effort_field, tracker=issue_tracker)

    budget_field = CustomField.objects.create(
        workspace=workspace,
        name="Бюджетный код",
        field_format=CustomField.FieldFormat.STRING,
        position=0,
    )
    CustomFieldTracker.objects.create(custom_field=budget_field, tracker=project_tracker)


def get_content_type(model_class):
    return ContentType.objects.get_for_model(model_class)


def serialize_custom_values(obj) -> list[dict]:
    content_type = get_content_type(obj.__class__)
    values = CustomValue.objects.filter(
        content_type=content_type,
        object_id=obj.pk,
    ).select_related("custom_field")
    return [
        {
            "field_id": value.custom_field_id,
            "field_name": value.custom_field.name,
            "field_format": value.custom_field.field_format,
            "value": value.value,
        }
        for value in values
    ]


def get_fields_for_tracker(tracker: Tracker | None) -> list[CustomField]:
    if tracker is None:
        return []
    return list(
        tracker.custom_fields.order_by("position", "id").prefetch_related("enumerations")
    )


def serialize_field_definition(field: CustomField) -> dict:
    return {
        "id": field.id,
        "name": field.name,
        "field_format": field.field_format,
        "description": field.description,
        "is_required": field.is_required,
        "position": field.position,
        "default_value": field.default_value,
        "tracker_ids": list(field.trackers.values_list("id", flat=True)),
        "enumerations": [
            {
                "id": item.id,
                "name": item.name,
                "position": item.position,
                "is_active": item.is_active,
                "parent_id": item.parent_id,
            }
            for item in field.enumerations.order_by("position", "id")
        ],
    }


@transaction.atomic
def save_custom_values(obj, values: dict[str, str]) -> None:
    if not values:
        return
    content_type = get_content_type(obj.__class__)
    field_ids = [int(key) for key in values]
    fields = {
        field.id: field
        for field in CustomField.objects.filter(pk__in=field_ids)
    }
    for key, raw in values.items():
        field_id = int(key)
        field = fields.get(field_id)
        if field is None:
            continue
        CustomValue.objects.update_or_create(
            custom_field=field,
            content_type=content_type,
            object_id=obj.pk,
            defaults={"value": raw or ""},
        )


def delete_custom_values_for_object(obj) -> None:
    content_type = get_content_type(obj.__class__)
    CustomValue.objects.filter(content_type=content_type, object_id=obj.pk).delete()
