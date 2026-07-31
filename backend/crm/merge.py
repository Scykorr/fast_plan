"""Org/Person merge and duplicate detection (P10 sprint 3)."""

from __future__ import annotations

import re

from django.db import transaction
from rest_framework.exceptions import ValidationError

from crm.models import Organization, OrganizationMembership, OrganizationTag, Person, PersonTag


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D+", "", phone or "")
    if len(digits) > 10 and digits.startswith("8"):
        digits = "7" + digits[1:]
    return digits


def _coalesce_text(survivor, loser, fields: list[str]) -> list[str]:
    updated: list[str] = []
    for field in fields:
        if not getattr(survivor, field) and getattr(loser, field):
            setattr(survivor, field, getattr(loser, field))
            updated.append(field)
    return updated


def find_duplicate_people(workspace) -> list[dict]:
    """Return candidate duplicate groups keyed by email or normalized phone."""
    people = list(
        Person.objects.filter(workspace=workspace)
        .order_by("id")
        .only("id", "full_name", "email", "phone")
    )
    by_email: dict[str, list[Person]] = {}
    by_phone: dict[str, list[Person]] = {}
    for person in people:
        email = (person.email or "").strip().lower()
        if email:
            by_email.setdefault(email, []).append(person)
        phone = normalize_phone(person.phone)
        if len(phone) >= 7:
            by_phone.setdefault(phone, []).append(person)

    groups: list[dict] = []
    seen_pairs: set[tuple[int, int]] = set()

    def add_group(reason: str, key: str, rows: list[Person]) -> None:
        if len(rows) < 2:
            return
        ids = sorted(p.id for p in rows)
        for i, left in enumerate(ids):
            for right in ids[i + 1 :]:
                pair = (left, right)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                a = next(p for p in rows if p.id == left)
                b = next(p for p in rows if p.id == right)
                groups.append(
                    {
                        "reason": reason,
                        "key": key,
                        "survivor_id": a.id,
                        "source_id": b.id,
                        "people": [
                            {
                                "id": a.id,
                                "full_name": a.full_name,
                                "email": a.email,
                                "phone": a.phone,
                            },
                            {
                                "id": b.id,
                                "full_name": b.full_name,
                                "email": b.email,
                                "phone": b.phone,
                            },
                        ],
                    }
                )

    for key, rows in by_email.items():
        add_group("email", key, rows)
    for key, rows in by_phone.items():
        add_group("phone", key, rows)
    return groups


def find_duplicate_organizations(workspace) -> list[dict]:
    orgs = list(
        Organization.objects.filter(workspace=workspace)
        .order_by("id")
        .only("id", "name", "website", "industry")
    )
    by_name: dict[str, list[Organization]] = {}
    by_website: dict[str, list[Organization]] = {}
    for org in orgs:
        key = re.sub(r"\s+", " ", (org.name or "").strip().lower())
        if key:
            by_name.setdefault(key, []).append(org)
        website = (org.website or "").strip().lower().rstrip("/")
        if website:
            by_website.setdefault(website, []).append(org)

    groups: list[dict] = []
    seen_pairs: set[tuple[int, int]] = set()

    def add_group(reason: str, key: str, rows: list[Organization]) -> None:
        if len(rows) < 2:
            return
        ids = sorted(o.id for o in rows)
        for i, left in enumerate(ids):
            for right in ids[i + 1 :]:
                pair = (left, right)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                a = next(o for o in rows if o.id == left)
                b = next(o for o in rows if o.id == right)
                groups.append(
                    {
                        "reason": reason,
                        "key": key,
                        "survivor_id": a.id,
                        "source_id": b.id,
                        "organizations": [
                            {
                                "id": a.id,
                                "name": a.name,
                                "website": a.website,
                                "industry": a.industry,
                            },
                            {
                                "id": b.id,
                                "name": b.name,
                                "website": b.website,
                                "industry": b.industry,
                            },
                        ],
                    }
                )

    for key, rows in by_name.items():
        add_group("name", key, rows)
    for key, rows in by_website.items():
        add_group("website", key, rows)
    return groups


@transaction.atomic
def merge_people(*, survivor: Person, source: Person) -> Person:
    if survivor.pk == source.pk:
        raise ValidationError({"source_id": "Cannot merge a person into itself."})
    if survivor.workspace_id != source.workspace_id:
        raise ValidationError({"source_id": "People must be in the same workspace."})

    updated = _coalesce_text(
        survivor,
        source,
        [
            "email",
            "phone",
            "telegram",
            "whatsapp",
            "job_title",
            "notes",
        ],
    )
    if not survivor.birth_date and source.birth_date:
        survivor.birth_date = source.birth_date
        updated.append("birth_date")
    if not survivor.owner_id and source.owner_id:
        survivor.owner_id = source.owner_id
        updated.append("owner")
    if not survivor.user_id and source.user_id:
        survivor.user_id = source.user_id
        updated.append("user")
    if not survivor.legacy_contact_id and source.legacy_contact_id:
        survivor.legacy_contact_id = source.legacy_contact_id
        updated.append("legacy_contact")
    if source.social_urls:
        merged_urls = list(dict.fromkeys([*(survivor.social_urls or []), *source.social_urls]))
        if merged_urls != (survivor.social_urls or []):
            survivor.social_urls = merged_urls
            updated.append("social_urls")
    if updated:
        survivor.save(update_fields=[*updated, "updated_at"])

    # Memberships (unique org+person)
    surviving_orgs = set(
        OrganizationMembership.objects.filter(person=survivor).values_list(
            "organization_id", flat=True
        )
    )
    for membership in list(OrganizationMembership.objects.filter(person=source)):
        if membership.organization_id in surviving_orgs:
            membership.delete()
        else:
            membership.person = survivor
            membership.save(update_fields=["person"])
            surviving_orgs.add(membership.organization_id)

    # Tags
    surviving_tags = set(
        PersonTag.objects.filter(person=survivor).values_list("tag_id", flat=True)
    )
    for link in list(PersonTag.objects.filter(person=source)):
        if link.tag_id in surviving_tags:
            link.delete()
        else:
            link.person = survivor
            link.save(update_fields=["person"])
            surviving_tags.add(link.tag_id)

    # Segments M2M
    for segment in list(source.segments.all()):
        segment.people.add(survivor)
        segment.people.remove(source)

    # Project links (unique project+person)
    surviving_projects = set(
        source.project_links.model.objects.filter(person=survivor).values_list(
            "project_id", flat=True
        )
    )
    for link in list(source.project_links.all()):
        if link.project_id in surviving_projects:
            link.delete()
        else:
            link.person = survivor
            link.save(update_fields=["person"])
            surviving_projects.add(link.project_id)

    # Plain FK rewrites
    source.activities.update(person=survivor)
    source.comments.update(person=survivor)
    source.attachments.update(person=survivor)
    source.deals.update(person=survivor)
    source.leads.update(person=survivor)
    source.documents.update(person=survivor)
    source.custom_field_values.update(person=survivor)
    source.stakeholder_records.update(person=survivor)

    source.delete()
    return survivor


@transaction.atomic
def merge_organizations(*, survivor: Organization, source: Organization) -> Organization:
    if survivor.pk == source.pk:
        raise ValidationError({"source_id": "Cannot merge an organization into itself."})
    if survivor.workspace_id != source.workspace_id:
        raise ValidationError({"source_id": "Organizations must be in the same workspace."})

    updated = _coalesce_text(
        survivor,
        source,
        ["website", "industry", "notes"],
    )
    if not survivor.owner_id and source.owner_id:
        survivor.owner_id = source.owner_id
        updated.append("owner")
    if updated:
        survivor.save(update_fields=[*updated, "updated_at"])

    surviving_people = set(
        OrganizationMembership.objects.filter(organization=survivor).values_list(
            "person_id", flat=True
        )
    )
    for membership in list(OrganizationMembership.objects.filter(organization=source)):
        if membership.person_id in surviving_people:
            membership.delete()
        else:
            membership.organization = survivor
            membership.save(update_fields=["organization"])
            surviving_people.add(membership.person_id)

    surviving_tags = set(
        OrganizationTag.objects.filter(organization=survivor).values_list(
            "tag_id", flat=True
        )
    )
    for link in list(OrganizationTag.objects.filter(organization=source)):
        if link.tag_id in surviving_tags:
            link.delete()
        else:
            link.organization = survivor
            link.save(update_fields=["organization"])
            surviving_tags.add(link.tag_id)

    for segment in list(source.segments.all()):
        segment.organizations.add(survivor)
        segment.organizations.remove(source)

    source.activities.update(organization=survivor)
    source.comments.update(organization=survivor)
    source.attachments.update(organization=survivor)
    source.deals.update(organization=survivor)
    source.leads.update(organization=survivor)
    source.documents.update(organization=survivor)
    source.custom_field_values.update(organization=survivor)
    source.client_projects.update(client_organization=survivor)
    source.finance_transactions.update(organization=survivor)
    source.process_instances.update(organization=survivor)

    source.delete()
    return survivor


def resolve_person_pair(workspace, survivor_id: int, source_id: int) -> tuple[Person, Person]:
    survivor = Person.objects.filter(workspace=workspace, pk=survivor_id).first()
    source = Person.objects.filter(workspace=workspace, pk=source_id).first()
    if survivor is None or source is None:
        raise ValidationError({"detail": "Person not found."})
    return survivor, source


def resolve_org_pair(
    workspace, survivor_id: int, source_id: int
) -> tuple[Organization, Organization]:
    survivor = Organization.objects.filter(workspace=workspace, pk=survivor_id).first()
    source = Organization.objects.filter(workspace=workspace, pk=source_id).first()
    if survivor is None or source is None:
        raise ValidationError({"detail": "Organization not found."})
    return survivor, source
