"""Helpers for CRM custom field definitions and values."""

from __future__ import annotations

from rest_framework.exceptions import ValidationError

from crm.models import (
    CrmCustomFieldDefinition,
    CrmCustomFieldValue,
    Deal,
    Lead,
    Organization,
    Person,
)

TARGET_MODEL = {
    CrmCustomFieldDefinition.Target.ORGANIZATION: Organization,
    CrmCustomFieldDefinition.Target.PERSON: Person,
    CrmCustomFieldDefinition.Target.DEAL: Deal,
    CrmCustomFieldDefinition.Target.LEAD: Lead,
}

TARGET_FK = {
    CrmCustomFieldDefinition.Target.ORGANIZATION: "organization",
    CrmCustomFieldDefinition.Target.PERSON: "person",
    CrmCustomFieldDefinition.Target.DEAL: "deal",
    CrmCustomFieldDefinition.Target.LEAD: "lead",
}


def coerce_value(definition: CrmCustomFieldDefinition, raw):
    ft = definition.field_type
    if raw is None or raw == "":
        if definition.required:
            raise ValidationError({definition.key: "Required."})
        return None
    if ft == CrmCustomFieldDefinition.FieldType.TEXT:
        return str(raw)[:2000]
    if ft == CrmCustomFieldDefinition.FieldType.NUMBER:
        try:
            return float(raw)
        except (TypeError, ValueError) as exc:
            raise ValidationError({definition.key: "Number required."}) from exc
    if ft == CrmCustomFieldDefinition.FieldType.BOOL:
        if isinstance(raw, bool):
            return raw
        if str(raw).lower() in ("1", "true", "yes", "on"):
            return True
        if str(raw).lower() in ("0", "false", "no", "off"):
            return False
        raise ValidationError({definition.key: "Boolean required."})
    if ft == CrmCustomFieldDefinition.FieldType.DATE:
        return str(raw)[:32]
    if ft == CrmCustomFieldDefinition.FieldType.SELECT:
        options = [str(o) for o in (definition.options or [])]
        val = str(raw)
        if options and val not in options:
            raise ValidationError({definition.key: "Invalid option."})
        return val
    if ft == CrmCustomFieldDefinition.FieldType.MULTI_SELECT:
        if not isinstance(raw, list):
            raise ValidationError({definition.key: "List required."})
        options = {str(o) for o in (definition.options or [])}
        vals = [str(x) for x in raw]
        if options and any(v not in options for v in vals):
            raise ValidationError({definition.key: "Invalid option."})
        return vals
    return raw


def list_definitions(workspace, target: str | None = None, *, active_only: bool = True):
    qs = CrmCustomFieldDefinition.objects.filter(workspace=workspace)
    if target:
        qs = qs.filter(target=target)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by("target", "position", "id")


def values_map(workspace, target: str, entity_id: int) -> dict:
    fk = TARGET_FK.get(target)
    if not fk:
        return {}
    defs = {
        d.id: d
        for d in list_definitions(workspace, target)
    }
    if not defs:
        return {}
    filt = {fk: entity_id, "definition_id__in": defs.keys()}
    rows = CrmCustomFieldValue.objects.filter(**filt).select_related("definition")
    out = {d.key: None for d in defs.values()}
    for row in rows:
        out[row.definition.key] = row.value
    return out


def set_values(workspace, target: str, entity_id: int, payload: dict) -> dict:
    if target not in TARGET_FK:
        raise ValidationError({"target": "Invalid target."})
    model = TARGET_MODEL[target]
    entity = model.objects.filter(workspace=workspace, pk=entity_id).first()
    if entity is None:
        raise ValidationError({"id": "Not found."})
    fk = TARGET_FK[target]
    defs = {d.key: d for d in list_definitions(workspace, target)}
    for key, raw in (payload or {}).items():
        definition = defs.get(key)
        if definition is None:
            continue
        value = coerce_value(definition, raw)
        defaults = {"value": value, fk: entity}
        # clear other FKs implicitly by create kwargs
        lookup = {"definition": definition, fk: entity}
        CrmCustomFieldValue.objects.update_or_create(
            **lookup,
            defaults={"value": value},
        )
        _ = defaults
    return values_map(workspace, target, entity_id)


def validate_definition_options(field_type: str, options) -> list:
    if field_type in (
        CrmCustomFieldDefinition.FieldType.SELECT,
        CrmCustomFieldDefinition.FieldType.MULTI_SELECT,
    ):
        if not isinstance(options, list):
            raise ValidationError({"options": "List of strings required."})
        return [str(o)[:120] for o in options]
    return []
