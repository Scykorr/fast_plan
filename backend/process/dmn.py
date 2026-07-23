"""DMN evaluation helpers (P8b)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("fast_plan")


def evaluate_decision(*, workspace, decision_key: str, inputs: dict[str, Any]) -> Any:
    """
    Evaluate a stored DMN table.

    SpiffWorkflow DMN parsing varies by version; we provide a resilient path:
    1) Try SpiffWorkflow BpmnDmnParser when XML is valid.
    2) Fallback: simple JSON rules embedded in DecisionDefinition via
       optional `rules` JSON in a companion approach — for XML-only tables,
       return first matching hit from a minimal table parser.
    """
    from process.models import DecisionDefinition

    decision = (
        DecisionDefinition.objects.filter(workspace=workspace, key=decision_key)
        .order_by("-version")
        .first()
    )
    if decision is None:
        raise ValueError(f"Decision {decision_key} not found")

    try:
        return _evaluate_with_spiff(decision.dmn_xml, decision.decision_id, inputs)
    except Exception as exc:  # noqa: BLE001
        logger.info("Spiff DMN failed (%s); using lite evaluator", exc)
        return _evaluate_lite(decision.dmn_xml, inputs)


def _evaluate_with_spiff(dmn_xml: str, decision_id: str, inputs: dict) -> Any:
    # Prefer Spiff when available; raise to fall back on lite.
    from SpiffWorkflow.dmn.parser.BpmnDmnParser import BpmnDmnParser
    from SpiffWorkflow.bpmn.PythonScriptEngine import PythonScriptEngine

    parser = BpmnDmnParser()
    raw = dmn_xml.encode("utf-8") if isinstance(dmn_xml, str) else dmn_xml
    # Some Spiff versions expose add_dmn_str / add_dmn_xml
    if hasattr(parser, "add_dmn_str"):
        parser.add_dmn_str(raw)
    elif hasattr(parser, "add_dmn_xml"):
        from lxml import etree

        parser.add_dmn_xml(etree.fromstring(raw))
    else:
        raise RuntimeError("DMN parser API unavailable")

    decision = parser.get_decision(decision_id)
    engine = PythonScriptEngine()
    result = decision.evaluate(inputs, engine)
    return result


def _evaluate_lite(dmn_xml: str, inputs: dict) -> Any:
    """
    Minimal hit-policy FIRST evaluator for simple decision tables encoded as:

      <!--fp-rules
      [{"when": {"score_gte": 70}, "then": {"route": "sales_lead"}}, ...]
      -->
    """
    import json
    import re

    match = re.search(r"<!--fp-rules\s*(\[.*?\])\s*-->", dmn_xml, re.DOTALL)
    if not match:
        return {"matched": False, "inputs": inputs}
    rules = json.loads(match.group(1))
    for rule in rules:
        when = rule.get("when") or {}
        ok = True
        for key, expected in when.items():
            if key.endswith("_gte"):
                field = key[:-4]
                if float(inputs.get(field, 0) or 0) < float(expected):
                    ok = False
                    break
            elif key.endswith("_lte"):
                field = key[:-4]
                if float(inputs.get(field, 0) or 0) > float(expected):
                    ok = False
                    break
            elif inputs.get(key) != expected:
                ok = False
                break
        if ok:
            return {"matched": True, **(rule.get("then") or {})}
    return {"matched": False}
