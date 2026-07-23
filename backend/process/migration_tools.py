"""P6e AutomationRule → BPMN stub generator (P8f)."""

from __future__ import annotations


SIMPLE_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
  id="Defs_{key}" targetNamespace="http://fastplan.local/bpmn">
  <bpmn:process id="{process_id}" name="{name}" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1" name="Start">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:userTask id="Activity_Review" name="Review automation: {name}">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:serviceTask id="Activity_Service" name="noop">
      <bpmn:incoming>Flow_2</bpmn:incoming>
      <bpmn:outgoing>Flow_3</bpmn:outgoing>
    </bpmn:serviceTask>
    <bpmn:endEvent id="EndEvent_1" name="End">
      <bpmn:incoming>Flow_3</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Activity_Review" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Activity_Review" targetRef="Activity_Service" />
    <bpmn:sequenceFlow id="Flow_3" sourceRef="Activity_Service" targetRef="EndEvent_1" />
  </bpmn:process>
</bpmn:definitions>
"""


def automation_rule_to_bpmn(rule) -> dict:
    """
    Convert a CRM AutomationRule into a draft ProcessDefinition payload.
    Does not save — caller creates the definition.
    """
    key = f"migrated-{rule.id}-{rule.name}".lower().replace(" ", "-")[:80]
    process_id = f"Process_{rule.id}"
    xml = SIMPLE_TEMPLATE.format(
        key=key.replace("-", "_"),
        process_id=process_id,
        name=_xml_escape(rule.name or f"Rule {rule.id}"),
    )
    return {
        "key": key,
        "name": f"[migrated] {rule.name}",
        "description": (
            f"Migrated from AutomationRule #{rule.id} "
            f"(trigger={rule.trigger}). Review and refine gateways/actions."
        ),
        "bpmn_xml": xml,
        "process_id": process_id,
        "category": rule.trigger or "",
        "source_automation_rule_id": rule.id,
    }


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
