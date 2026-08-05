# ADR: Waterfall = projects methodology + gates (not a separate app)

**Status:** Accepted (2026-08-05)  
**Context:** Fast Plan already has PMBOK-style predictive primitives (WBS, FS/Gantt, milestones, baselines, change requests). Scrum needed a separate app because Product Backlog / Sprint / story points are not WBS concepts. Waterfall does not.

## Decision

1. **No** `backend/waterfall/` Django app mirroring `backend/scrum/`.
2. Extend **`projects`**: `Project.methodology` (`predictive` | `scrum` | `hybrid`), `Project.schedule_locked`, L1 `WBSNode.phase_key` / `gate_status`, and `PhaseGate` decisions.
3. Seed classic SDLC phases via `POST /api/projects/<id>/waterfall/` (Requirements → Design → Implementation → Verification → Maintenance) with FS links and gate milestones.
4. Gate **pass** creates a baseline and locks schedule; structural/date edits return **409** until a Change Request is **approved** (unlocks).
5. Process pack `waterfall_phase_gate` is optional BPMN glue; phase unlock truth stays in `projects`.

## Consequences

- Predictive projects hide the Scrum tab; scrum hides Waterfall; hybrid shows both.
- Gantt / Baseline / CR remain the primary execution and change-control surfaces.
- ROADMAP P3 “Stage / phase gates” is implemented as Waterfall phase gates on the project.

## Related

- [`ROADMAP.md`](../ROADMAP.md) — methodology backlog  
- Contrast: [`backend/scrum/`](../backend/scrum/) for iterative delivery
