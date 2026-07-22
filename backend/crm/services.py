"""CRM helpers: legacy sync, stale contacts, segment rules."""

from datetime import timedelta

from django.db.models import Max, Q, QuerySet
from django.utils import timezone

from birthdays.models import Contact
from crm.models import Organization, Person, ProjectPersonLink, Segment, Tag
from projects.models import Project, Stakeholder


def sync_contact_to_person(contact: Contact) -> Person:
    existing = Person.objects.filter(legacy_contact=contact).first()
    birth = getattr(contact, "birthday", None)
    defaults = {
        "full_name": contact.name,
        "notes": contact.notes or "",
        "job_title": contact.relation or "",
        "birth_date": birth.birth_date if birth else None,
        "remind_before_days": birth.remind_before_days if birth else 7,
    }
    if existing:
        for key, value in defaults.items():
            setattr(existing, key, value)
        existing.save()
        return existing
    return Person.objects.create(
        workspace=contact.workspace,
        legacy_contact=contact,
        **defaults,
    )


def sync_workspace_contacts(workspace) -> int:
    count = 0
    qs = Contact.objects.filter(workspace=workspace).select_related("birthday")
    for contact in qs:
        sync_contact_to_person(contact)
        count += 1
    return count


def sync_stakeholder_to_person(stakeholder: Stakeholder) -> tuple[Person, ProjectPersonLink]:
    workspace = stakeholder.project.workspace
    person = None
    if stakeholder.contact_email:
        person = Person.objects.filter(
            workspace=workspace, email__iexact=stakeholder.contact_email
        ).first()
    if person is None:
        person = Person.objects.filter(
            workspace=workspace, full_name__iexact=stakeholder.name
        ).first()
    if person is None:
        person = Person.objects.create(
            workspace=workspace,
            full_name=stakeholder.name,
            email=stakeholder.contact_email or "",
            notes=stakeholder.notes or "",
            job_title=stakeholder.role or "",
        )
    else:
        changed = False
        if stakeholder.contact_email and not person.email:
            person.email = stakeholder.contact_email
            changed = True
        if stakeholder.notes and not person.notes:
            person.notes = stakeholder.notes
            changed = True
        if changed:
            person.save()

    link, _ = ProjectPersonLink.objects.update_or_create(
        project=stakeholder.project,
        person=person,
        defaults={
            "role_kind": ProjectPersonLink.RoleKind.STAKEHOLDER,
            "role_label": stakeholder.role or "",
            "interest": stakeholder.interest,
            "influence": stakeholder.influence,
            "notes": stakeholder.notes or "",
            "stakeholder": stakeholder,
        },
    )
    if stakeholder.person_id != person.id:
        stakeholder.person = person
        stakeholder.save(update_fields=["person"])
    return person, link


def sync_project_stakeholders(project: Project) -> int:
    count = 0
    for stakeholder in project.stakeholders.all():
        sync_stakeholder_to_person(stakeholder)
        count += 1
    return count


def ensure_default_client_org(workspace, name: str = "Клиенты") -> Organization:
    org, _ = Organization.objects.get_or_create(
        workspace=workspace,
        name=name,
        defaults={"notes": "Создано автоматически при импорте CRM"},
    )
    return org


DEFAULT_PIPELINE_STAGES = (
    ("Лид", 10, False, False),
    ("Квалификация", 25, False, False),
    ("Предложение", 50, False, False),
    ("Переговоры", 75, False, False),
    ("Выиграно", 100, True, False),
    ("Проиграно", 0, False, True),
)


def ensure_default_pipeline(workspace):
    from crm.models import Pipeline, PipelineStage

    pipeline = Pipeline.objects.filter(workspace=workspace, is_default=True).first()
    if pipeline is None:
        pipeline = Pipeline.objects.create(
            workspace=workspace, name="Продажи", is_default=True
        )
    if not pipeline.stages.exists():
        for index, (name, probability, is_won, is_lost) in enumerate(
            DEFAULT_PIPELINE_STAGES
        ):
            PipelineStage.objects.create(
                pipeline=pipeline,
                name=name,
                position=index,
                default_probability=probability,
                is_won=is_won,
                is_lost=is_lost,
            )
    return pipeline


def annotate_last_activity(qs: QuerySet, *, person: bool = True) -> QuerySet:
    if person:
        return qs.annotate(last_activity_at=Max("activities__occurred_at"))
    return qs.annotate(last_activity_at=Max("activities__occurred_at"))


def filter_stale(qs: QuerySet, stale_days: int) -> QuerySet:
    cutoff = timezone.now() - timedelta(days=stale_days)
    return qs.filter(Q(last_activity_at__lt=cutoff) | Q(last_activity_at__isnull=True))


def days_since_touch(last_activity_at) -> int | None:
    if last_activity_at is None:
        return None
    delta = timezone.now() - last_activity_at
    return max(0, delta.days)


def resolve_segment_people(segment: Segment) -> QuerySet[Person]:
    workspace = segment.workspace
    if segment.kind == Segment.Kind.MANUAL:
        return segment.people.all()

    rule = segment.rule or {}
    qs = Person.objects.filter(workspace=workspace)
    tag_name = (rule.get("tag") or "").strip()
    if tag_name:
        qs = qs.filter(tag_links__tag__name__iexact=tag_name)
    stale_days = rule.get("stale_days")
    if stale_days is not None:
        try:
            days = int(stale_days)
        except (TypeError, ValueError):
            days = None
        if days is not None and days > 0:
            qs = annotate_last_activity(qs)
            qs = filter_stale(qs, days)
    return qs.distinct()


def resolve_segment_organizations(segment: Segment) -> QuerySet[Organization]:
    workspace = segment.workspace
    if segment.kind == Segment.Kind.MANUAL:
        return segment.organizations.all()

    rule = segment.rule or {}
    qs = Organization.objects.filter(workspace=workspace)
    tag_name = (rule.get("tag") or "").strip()
    if tag_name:
        qs = qs.filter(tag_links__tag__name__iexact=tag_name)
    stale_days = rule.get("stale_days")
    if stale_days is not None:
        try:
            days = int(stale_days)
        except (TypeError, ValueError):
            days = None
        if days is not None and days > 0:
            qs = annotate_last_activity(qs, person=False)
            qs = filter_stale(qs, days)
    return qs.distinct()


def get_or_create_tag(workspace, name: str, color: str = "#3b82f6") -> Tag:
    name = (name or "").strip()
    tag, _ = Tag.objects.get_or_create(
        workspace=workspace,
        name=name,
        defaults={"color": color or "#3b82f6"},
    )
    return tag
