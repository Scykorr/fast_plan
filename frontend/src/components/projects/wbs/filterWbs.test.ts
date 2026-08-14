import { describe, expect, it } from "vitest";

import type { WBSNode } from "../../../api/projects";
import {
  collectWbsAssignees,
  collectWbsObsRoles,
  collectWbsOrgUnits,
  collectWbsStatuses,
  filterWbsTree,
} from "./filterWbs";

function node(
  partial: Partial<WBSNode> & Pick<WBSNode, "id" | "title">,
): WBSNode {
  return {
    code: String(partial.id),
    description: "",
    node_type: "work_package",
    position: 0,
    parent_id: null,
    tracker_id: null,
    tracker_name: null,
    workflow_status_id: null,
    workflow_status_name: null,
    assignee_id: null,
    assignee_name: null,
    custom_values: [],
    schedule: null,
    card_id: null,
    children: [],
    ...partial,
  };
}

const tree: WBSNode[] = [
  node({
    id: 1,
    title: "Root",
    node_type: "deliverable",
    children: [
      node({
        id: 2,
        title: "A",
        parent_id: 1,
        assignee_id: 10,
        assignee_name: "Alice",
        workflow_status_id: 1,
        workflow_status_name: "Новая",
      }),
      node({
        id: 3,
        title: "B",
        parent_id: 1,
        assignee_id: 20,
        assignee_name: "Bob",
        workflow_status_id: 2,
        workflow_status_name: "В работе",
        children: [
          node({
            id: 4,
            title: "B1",
            parent_id: 3,
            assignee_id: 10,
            assignee_name: "Alice",
            org_unit_id: 100,
            org_unit_name: "QA",
            obs_role_id: 200,
            obs_role_name: "Tester",
            workflow_status_id: 2,
            workflow_status_name: "В работе",
          }),
        ],
      }),
    ],
  }),
];

describe("filterWbsTree", () => {
  it("returns original tree when filters are empty", () => {
    expect(filterWbsTree(tree, {})).toBe(tree);
  });

  it("keeps ancestors of matching nodes", () => {
    const filtered = filterWbsTree(tree, { assigneeId: 10 });
    expect(filtered).toHaveLength(1);
    expect(filtered[0].children.map((c) => c.id)).toEqual([2, 3]);
    expect(filtered[0].children[1].children.map((c) => c.id)).toEqual([4]);
  });

  it("filters by status", () => {
    const filtered = filterWbsTree(tree, { statusId: 1 });
    expect(filtered[0].children.map((c) => c.id)).toEqual([2]);
  });

  it("filters by org unit and OBS role", () => {
    const byUnit = filterWbsTree(tree, { orgUnitId: 100 });
    expect(byUnit[0].children.map((c) => c.id)).toEqual([3]);
    expect(byUnit[0].children[0].children.map((c) => c.id)).toEqual([4]);

    const byRole = filterWbsTree(tree, { obsRoleId: 200 });
    expect(byRole[0].children.map((c) => c.id)).toEqual([3]);
  });

  it("collects unique assignees and statuses", () => {
    expect(collectWbsAssignees(tree).map((a) => a.id)).toEqual([10, 20]);
    expect(collectWbsStatuses(tree).map((s) => s.name)).toEqual([
      "В работе",
      "Новая",
    ]);
    expect(collectWbsOrgUnits(tree).map((u) => u.name)).toEqual(["QA"]);
    expect(collectWbsObsRoles(tree).map((r) => r.name)).toEqual(["Tester"]);
  });
});
