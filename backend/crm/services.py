"""Legacy sync: birthday Contact / Stakeholder → CRM Person directory."""

from birthdays.models import Contact
from crm.models import Organization, Person, ProjectPersonLink
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
