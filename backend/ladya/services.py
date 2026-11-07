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


def sha256_of_upload(upload: BinaryIO, *, chunk_size: int = 1024 * 1024) -> str:
    """Stream hash — do not load the whole file into RAM."""
    digest = hashlib.sha256()
    pos = upload.tell() if hasattr(upload, "tell") else None
    if hasattr(upload, "seek"):
        upload.seek(0)
    if hasattr(upload, "chunks"):
        for chunk in upload.chunks(chunk_size):
            if chunk:
                digest.update(chunk)
    else:
        while True:
            chunk = upload.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    if hasattr(upload, "seek"):
        upload.seek(pos if pos is not None else 0)
    return digest.hexdigest()


TRANSFER_ALLOWED_STATUSES = {
    Package.Status.ACCEPTED,
    Package.Status.IN_PROGRESS,
    Package.Status.RETURNED,
}


@transaction.atomic
def transfer_package(
    package: Package,
    *,
    to_laboratory,
    user,
    reason: str = "",
) -> Package:
    if package.status not in TRANSFER_ALLOWED_STATUSES:
        raise ValidationError(
            {
                "status": (
                    f"Передача из статуса {package.status} запрещена. "
                    f"Допустимо: {sorted(TRANSFER_ALLOWED_STATUSES)}."
                )
            }
        )
    if to_laboratory is None:
        raise ValidationError({"to_laboratory": "Укажите целевую лабораторию."})
    if to_laboratory.workspace_id != package.workspace_id:
        raise ValidationError({"to_laboratory": "Лаборатория из другого workspace."})
    if not to_laboratory.is_active:
        raise ValidationError({"to_laboratory": "Лаборатория неактивна."})
    from_lab = package.to_laboratory
    if from_lab and from_lab.id == to_laboratory.id:
        raise ValidationError({"to_laboratory": "Пакет уже в этой лаборатории."})
    package.to_laboratory = to_laboratory
    package.save(update_fields=["to_laboratory", "updated_at"])
    PackageStatusEvent.objects.create(
        package=package,
        from_status=package.status,
        to_status=package.status,
        from_laboratory=from_lab,
        to_laboratory=to_laboratory,
        reason=reason or "Передача между лабораториями",
        changed_by=user,
    )
    return package


@transaction.atomic
def create_delivery_task_from_package(package: Package, *, user):
    """Create Agent Ops DeliveryTask and link it; never auto-claims."""
    from delivery.models import DeliveryTask

    if package.linked_delivery_task_id:
        raise ValidationError(
            {"linked_delivery_task": "Пакет уже связан с DeliveryTask."}
        )
    task = DeliveryTask.objects.create(
        workspace=package.workspace,
        title=f"[Ladya {package.display_code}] {package.title}"[:255],
        description=package.summary or "",
        context=(
            f"Создано из пакета Ладьи {package.display_code} (id={package.pk}).\n"
            f"От: {package.from_laboratory_id} → Кому: {package.to_laboratory_id}"
        ),
        business_outcome=package.summary or package.title,
        created_by=user,
        status=DeliveryTask.Status.DRAFT,
        external_pack_url="",
    )
    package.linked_delivery_task = task
    package.save(update_fields=["linked_delivery_task", "updated_at"])
    PackageStatusEvent.objects.create(
        package=package,
        from_status=package.status,
        to_status=package.status,
        from_laboratory=package.to_laboratory,
        to_laboratory=package.to_laboratory,
        reason=f"Создана DeliveryTask #{task.id} (без auto-claim)",
        changed_by=user,
    )
    return task


def build_package_manifest(package: Package) -> dict:
    """Canonical package evidence. Omits volatile updated_at so sha256 stays stable on save."""
    files = [
        {
            "id": f.id,
            "original_name": f.original_name,
            "size": f.size,
            "sha256": f.sha256,
            "content_type": f.content_type,
        }
        for f in package.files.order_by("id")
    ]
    return {
        "package_id": package.id,
        "display_code": package.display_code,
        "public_number": package.public_number,
        "title": package.title,
        "status": package.status,
        "from_laboratory": package.from_laboratory_id,
        "to_laboratory": package.to_laboratory_id,
        "linked_delivery_task": package.linked_delivery_task_id,
        "created_at": package.created_at.isoformat(),
        "files": files,
    }


def canonical_manifest_json(manifest: dict) -> str:
    import json

    return json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def apply_manifest_sha256(package: Package) -> tuple[dict, str]:
    manifest = build_package_manifest(package)
    raw = canonical_manifest_json(manifest)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    package.manifest_sha256 = digest
    package.save(update_fields=["manifest_sha256", "updated_at"])
    return manifest, digest
