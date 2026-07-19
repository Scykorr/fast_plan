from audit.models import AuditLogEntry


def log_audit(
    workspace,
    actor,
    action: str,
    entity_type: str,
    entity_id=None,
    summary: str = "",
    changes: dict | None = None,
) -> AuditLogEntry:
    """Record an immutable audit trail entry for a workspace mutation."""
    actor_user = actor if actor is not None and getattr(actor, "is_authenticated", False) else None
    return AuditLogEntry.objects.create(
        workspace=workspace,
        actor=actor_user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        changes=changes or {},
    )
