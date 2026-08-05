# Waterfall phase gate (lite)

Training pack aligned with classic predictive / Waterfall exit gates — **not** a certification claim.

Flow: Submit phase package → Review checklist → Go/No-Go decision.

Use with project Waterfall tab: after a phase is `open`, start this process for formal review; record the product decision via `POST /api/projects/<id>/waterfall/gates/` (source of truth for unlock / baseline / schedule lock). Optional: store `process_instance` on `PhaseGate` when wiring automation later.
