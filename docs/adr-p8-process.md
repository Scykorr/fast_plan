# ADR: P8 Process — BPMN/DMN/CMMN engine choice

**Status:** Accepted (2026-07-23)  
**Context:** Fast Plan needs standards-based process management beyond P6e CRM automation (if-this-then-that).

## Decision

1. **Engine:** embed [SpiffWorkflow](https://github.com/sartography/SpiffWorkflow) in Django (`backend/process/`).
2. **Modeler/viewer:** [bpmn-js](https://bpmn.io/) on the frontend (industry-standard BPMN 2.0 notation for business users).
3. **Coexistence:** keep P6e `AutomationRule` for simple CRM rules; P8 for long-running, branching, human-in-the-loop processes.
4. **Compliance packs** (ISO 9001/PDCA, ITIL/COBIT, ISO 27001/NIST CSF): importable BPMN(+DMN) templates — **not** product certification claims.
5. **Not in MVP:** external Camunda/Flowable cluster, custom token engine, full process mining.

## Consequences

- Workspace-scoped definitions/deployments/instances/user tasks.
- Immutable deployments; running instances stay on the version they started.
- Executable BPMN MVP whitelist: Start/End, UserTask, ServiceTask, Exclusive/Parallel Gateway, Timer (via Celery), Message start (domain events).
- DMN, CMMN, form schemas, and packs land as phased follow-ups in the same app.

## Related

- Roadmap epic: **P8 Process** in [`ROADMAP.md`](../ROADMAP.md)
- BPM-lite: [`backend/crm/automation.py`](../backend/crm/automation.py)
