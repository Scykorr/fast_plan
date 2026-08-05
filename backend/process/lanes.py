"""Extract BPMN lanes from process definition XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _attr(el: ET.Element, name: str) -> str:
    return (
        el.attrib.get(name)
        or el.attrib.get(f"{{http://www.omg.org/spec/BPMN/20100524/MODEL}}{name}")
        or ""
    ).strip()


def extract_lanes(bpmn_xml: str) -> list[dict]:
    """Return [{lane_id, lane_name, flow_node_refs}] from BPMN XML."""
    if not (bpmn_xml or "").strip():
        return []
    try:
        root = ET.fromstring(bpmn_xml)
    except ET.ParseError:
        return []

    lanes: list[dict] = []
    for el in root.iter():
        if _local(el.tag) != "lane":
            continue
        lane_id = _attr(el, "id")
        if not lane_id:
            continue
        refs: list[str] = []
        for child in el:
            if _local(child.tag) != "flowNodeRef":
                continue
            ref = (child.text or "").strip() or _attr(child, "id")
            if ref:
                refs.append(ref)
        lanes.append(
            {
                "lane_id": lane_id,
                "lane_name": _attr(el, "name") or lane_id,
                "flow_node_refs": refs,
            }
        )
    return lanes
