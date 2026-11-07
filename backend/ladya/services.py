"""Domain helpers for Ladya Hub packages and intake."""

from __future__ import annotations

import hashlib
from typing import BinaryIO

from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from ladya.models import IntakeRequest, Package, PackageStatusEvent

PACKAGE_TRANSITIONS: dict[str, set[str]] = {
    Package.Status.DRAFT: {Package.Status.SUBMITTED, Package.Status.REJECTED},
    Package.Status.SUBMITTED: {
        Package.Status.ACCEPTED,
        Package.Status.REJECTED,
        Package.Status.RETURNED,
    },
    Package.Status.ACCEPTED: {
        Package.Status.IN_PROGRESS,
        Package.Status.RETURNED,
        Package.Status.REJECTED,
    },
    Package.Status.IN_PROGRESS: {
        Package.Status.RETURNED,
        Package.Status.CLOSED,
    },
    Package.Status.RETURNED: {
        Package.Status.SUBMITTED,
        Package.Status.ACCEPTED,
        Package.Status.IN_PROGRESS,
        Package.Status.CLOSED,
        Package.Status.REJECTED,
    },
    Package.Status.CLOSED: set(),
    Package.Status.REJECTED: set(),
}

INTAKE_TRANSITIONS: dict[str, set[str]] = {
    IntakeRequest.Status.NEW: {
        IntakeRequest.Status.TRIAGED,
        IntakeRequest.Status.CLOSED,
    },
    IntakeRequest.Status.TRIAGED: {
        IntakeRequest.Status.CONVERTED,
        IntakeRequest.Status.CLOSED,
    },
    IntakeRequest.Status.CONVERTED: {IntakeRequest.Status.CLOSED},
    IntakeRequest.Status.CLOSED: set(),
}


def next_package_number(workspace) -> int:
    current = (
        Package.objects.filter(workspace=workspace).aggregate(m=Max("public_number"))[
            "m"
        ]
        or 0
    )
    return current + 1


def assert_package_transition(current: str, target: str) -> None:
    allowed = PACKAGE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValidationError(
            {
                "status": (
                    f"Переход {current} → {target} запрещён. "
                    f"Допустимо: {sorted(allowed) or 'нет'}."
                )
            }
        )


def assert_intake_transition(current: str, target: str) -> None:
    allowed = INTAKE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValidationError(
            {
                "status": (
                    f"Переход {current} → {target} запрещён. "
                    f"Допустимо: {sorted(allowed) or 'нет'}."
                )
            }
        )


@transaction.atomic
def transition_package(
    package: Package,
    *,
    to_status: str,
    user,
    reason: str = "",
    to_laboratory=None,
) -> Package:
    assert_package_transition(package.status, to_status)
    from_status = package.status
    from_lab = package.to_laboratory
    if to_laboratory is not None:
        if to_laboratory.workspace_id != package.workspace_id:
            raise ValidationError(
                {"to_laboratory": "Лаборатория из другого workspace."}
            )
        package.to_laboratory = to_laboratory
    package.status = to_status
    package.save(
        update_fields=["status", "to_laboratory", "updated_at"]
        if to_laboratory is not None
        else ["status", "updated_at"]
    )
    PackageStatusEvent.objects.create(
        package=package,
        from_status=from_status,
        to_status=to_status,
        from_laboratory=from_lab,
        to_laboratory=package.to_laboratory,
        reason=reason or "",
        changed_by=user,
    )
    return package


@transaction.atomic
def convert_intake_to_package(
    intake: IntakeRequest,
    *,
    user,
    title: str,
    from_laboratory=None,
    to_laboratory=None,
    summary: str = "",
) -> Package:
    assert_intake_transition(intake.status, IntakeRequest.Status.CONVERTED)
    if intake.package_id:
        raise ValidationError({"package": "Обращение уже преобразовано в пакет."})
    package = Package.objects.create(
        workspace=intake.workspace,
        public_number=next_package_number(intake.workspace),
        title=title.strip() or f"Intake #{intake.pk}",
        summary=summary or intake.body,
        from_laboratory=from_laboratory,
        to_laboratory=to_laboratory,
        status=Package.Status.DRAFT,
        created_by=user,
        notes_limitations=f"Источник: intake #{intake.pk}; контакт: {intake.contact}",
    )
    PackageStatusEvent.objects.create(
        package=package,
        from_status="",
        to_status=Package.Status.DRAFT,
        from_laboratory=None,
        to_laboratory=to_laboratory,
        reason="Создан из IntakeRequest",
        changed_by=user,
    )
    intake.package = package
    intake.status = IntakeRequest.Status.CONVERTED
    intake.save(update_fields=["package", "status", "updated_at"])
    return package


def sha256_of_upload(upload: BinaryIO) -> str:
    digest = hashlib.sha256()
    pos = upload.tell() if hasattr(upload, "tell") else None
    if hasattr(upload, "seek"):
        upload.seek(0)
    for chunk in upload.chunks() if hasattr(upload, "chunks") else [upload.read()]:
        if not chunk:
            break
        digest.update(chunk)
    if hasattr(upload, "seek") and pos is not None:
        upload.seek(pos)
    elif hasattr(upload, "seek"):
        upload.seek(0)
    return digest.hexdigest()
