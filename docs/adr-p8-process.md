# ADR: P8 Process — BPMN/DMN/CMMN engine choice

**Status:** Accepted (2026-07-23), extended **P8g** (2026-07-23)  
**Context:** Fast Plan needs standards-based process management beyond P6e CRM automation (if-this-then-that).

## Decision

1. **Engine:** embed [SpiffWorkflow](https://github.com/sartography/SpiffWorkflow) in Django (`backend/process/`).
2. **Modeler/viewer:** [bpmn-js](https://bpmn.io/) on the frontend (industry-standard BPMN 2.0 notation for business users).
3. **Coexistence:** keep P6e `AutomationRule` for simple CRM rules; P8 for long-running, branching, human-in-the-loop processes.
4. **Compliance packs** (ISO 9001/PDCA, ITIL/COBIT, ISO 27001/NIST CSF): importable BPMN(+DMN) templates — **not** product certification claims.
5. **Not in scope (still):** external Camunda/Flowable cluster, custom token engine, Celonis-class process mining, full FEEL 1.1, Camunda CMMN engine.

## P8g follow-up (in-app advanced slice)

| Area | What we ship | Explicitly not |
|------|----------------|----------------|
| **Process mining** | Event log via `ActivityInstance`; DFG / top paths / bottlenecks at `GET /api/process/mining/` | Full discovery algorithms, conformance checking SaaS |
| **Advanced DMN** | OMG `decisionTable` XML evaluator (FIRST/UNIQUE) + FEEL-lite unary tests; Spiff when available; `<!--fp-rules-->` fallback; UI tab | Full FEEL / boxed expressions / DRD designer |
| **Richer CMMN** | `depends_on`, `required`, `available_items`, auto `process_key` on complete; close gated on required items | Full CMMN 1.1 interpreter / sentry lifecycle |

## Consequences

- Workspace-scoped definitions/deployments/instances/user tasks.
- Immutable deployments; running instances stay on the version they started.
- Executable BPMN MVP whitelist: Start/End, UserTask, ServiceTask, Exclusive/Parallel Gateway, Timer (via Celery), Message start (domain events).
- DMN, CMMN, form schemas, packs, mining lite — same Django app.

## Related

- Roadmap epic: **P8 Process** in [`ROADMAP.md`](../ROADMAP.md)
- BPM-lite: [`backend/crm/automation.py`](../backend/crm/automation.py)
