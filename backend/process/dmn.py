"""DMN evaluation (P8b + P8g advanced decision tables)."""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any

logger = logging.getLogger("fast_plan")


def evaluate_decision(*, workspace, decision_key: str, inputs: dict[str, Any]) -> Any:
    """
    Evaluate a stored DMN table.

    Order:
      1) SpiffWorkflow DMN (when available)
      2) OMG decisionTable XML (FIRST / UNIQUE hit policies, FEEL-lite)
      3) <!--fp-rules [...]--> JSON fallback
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
        logger.info("Spiff DMN failed (%s); trying table / lite", exc)

    table = _evaluate_decision_table(decision.dmn_xml, inputs)
    if table is not None:
        return table
    return _evaluate_lite(decision.dmn_xml, inputs)


def _evaluate_with_spiff(dmn_xml: str, decision_id: str, inputs: dict) -> Any:
    from SpiffWorkflow.dmn.parser.BpmnDmnParser import BpmnDmnParser
    from SpiffWorkflow.bpmn.PythonScriptEngine import PythonScriptEngine

    parser = BpmnDmnParser()
    raw = dmn_xml.encode("utf-8") if isinstance(dmn_xml, str) else dmn_xml
    if hasattr(parser, "add_dmn_str"):
        parser.add_dmn_str(raw)
    elif hasattr(parser, "add_dmn_xml"):
        from lxml import etree

        parser.add_dmn_xml(etree.fromstring(raw))
    else:
        raise RuntimeError("DMN parser API unavailable")

    decision = parser.get_decision(decision_id)
    engine = PythonScriptEngine()
    return decision.evaluate(inputs, engine)


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _find_decision_table(root: ET.Element) -> ET.Element | None:
    for el in root.iter():
        if _local(el.tag) == "decisionTable":
            return el
    return None


def _text_of(el: ET.Element | None) -> str:
    if el is None:
        return ""
    parts = [el.text or ""]
    for child in el:
        parts.append(_text_of(child))
        parts.append(child.tail or "")
    return "".join(parts).strip()


def _input_names(table: ET.Element) -> list[str]:
    names: list[str] = []
    for child in table:
        if _local(child.tag) != "input":
            continue
        expr = ""
        for sub in child:
            if _local(sub.tag) == "inputExpression":
                for t in sub:
                    if _local(t.tag) == "text":
                        expr = (t.text or "").strip()
        if not expr:
            expr = (
                child.attrib.get("label")
                or child.attrib.get("id")
                or f"input_{len(names)}"
            )
        names.append(expr)
    return names


def _output_names(table: ET.Element) -> list[str]:
    names: list[str] = []
    for child in table:
        if _local(child.tag) != "output":
            continue
        names.append(
            child.attrib.get("name")
            or child.attrib.get("label")
            or child.attrib.get("id")
            or f"output_{len(names)}"
        )
    return names


def _parse_literal(raw: str) -> Any:
    s = raw.strip()
    if not s:
        return ""
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return s


def _match_entry(entry_text: str, value: Any) -> bool:
    """FEEL-lite unary tests for a single input cell."""
    text = (entry_text or "").strip()
    if text in ("", "-", "null"):
        return True
    # Compound OR: a, b, c
    if "," in text and not any(op in text for op in (">=", "<=", "==", "!=", ">", "<")):
        return any(_match_entry(part.strip(), value) for part in text.split(","))

    m = re.match(r"^(>=|<=|==|!=|>|<)\s*(.+)$", text)
    if m:
        op, rhs_raw = m.group(1), m.group(2)
        rhs = _parse_literal(rhs_raw)
        try:
            left = float(value) if value is not None and value != "" else None
            right = float(rhs)
        except (TypeError, ValueError):
            left, right = value, rhs
        if left is None:
            return False
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        return False

    expected = _parse_literal(text)
    if isinstance(expected, (int, float)) and value is not None and value != "":
        try:
            return float(value) == float(expected)
        except (TypeError, ValueError):
            pass
    return value == expected


def _evaluate_decision_table(dmn_xml: str, inputs: dict) -> dict | None:
    """
    Parse OMG DMN decisionTable. Returns None if no table/rules found.
    Hit policies: FIRST (default), UNIQUE (first match; multiple → matched_unique=False).
    """
    try:
        # Strip HTML comments (fp-rules) before parse
        cleaned = re.sub(r"<!--.*?-->", "", dmn_xml, flags=re.DOTALL)
        root = ET.fromstring(cleaned)
    except ET.ParseError:
        return None

    table = _find_decision_table(root)
    if table is None:
        return None

    hit_policy = (table.attrib.get("hitPolicy") or "FIRST").upper()
    input_names = _input_names(table)
    output_names = _output_names(table)
    if not input_names and not output_names:
        return None

    matches: list[dict] = []
    for child in table:
        if _local(child.tag) != "rule":
            continue
        input_entries = [
            _text_of(el) for el in child if _local(el.tag) == "inputEntry"
        ]
        output_entries = [
            _text_of(el) for el in child if _local(el.tag) == "outputEntry"
        ]
        # Pad / trim to column counts
        while len(input_entries) < len(input_names):
            input_entries.append("")
        ok = True
        for name, entry in zip(input_names, input_entries):
            if not _match_entry(entry, inputs.get(name)):
                ok = False
                break
        if not ok:
            continue
        outputs: dict[str, Any] = {}
        for name, entry in zip(output_names, output_entries):
            outputs[name] = _parse_literal(entry) if entry.strip() else None
        matches.append(outputs)

    if not matches:
        # Table exists but no rules matched — still a table evaluation
        if any(_local(c.tag) == "rule" for c in table):
            return {"matched": False, "hit_policy": hit_policy, "inputs": inputs}
        return None

    if hit_policy == "UNIQUE" and len(matches) > 1:
        return {
            "matched": True,
            "matched_unique": False,
            "hit_policy": hit_policy,
            **matches[0],
            "all_matches": matches,
        }
    return {"matched": True, "hit_policy": hit_policy, **matches[0]}


def _evaluate_lite(dmn_xml: str, inputs: dict) -> Any:
    """
    Minimal hit-policy FIRST evaluator for:

      <!--fp-rules
      [{"when": {"score_gte": 70}, "then": {"route": "sales_lead"}}, ...]
      -->
    """
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
