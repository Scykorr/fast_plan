import type { WBSNode } from "../../../api/projects";

export type WbsFilter = {
  assigneeId?: number | null;
  statusId?: number | null;
};

export type FilterOption = {
  id: number;
  name: string;
};

function nodeMatches(node: WBSNode, filter: WbsFilter): boolean {
  if (
    filter.assigneeId != null &&
    node.assignee_id !== filter.assigneeId
  ) {
    return false;
  }
  if (
    filter.statusId != null &&
    node.workflow_status_id !== filter.statusId
  ) {
    return false;
  }
  return true;
}

/** Keep ancestors of matching nodes so the tree structure stays readable. */
export function filterWbsTree(
  nodes: WBSNode[],
  filter: WbsFilter,
): WBSNode[] {
  if (filter.assigneeId == null && filter.statusId == null) {
    return nodes;
  }

  const result: WBSNode[] = [];
  for (const node of nodes) {
    const children = filterWbsTree(node.children, filter);
    if (nodeMatches(node, filter) || children.length > 0) {
      result.push({ ...node, children });
    }
  }
  return result;
}

function walk(nodes: WBSNode[], visit: (node: WBSNode) => void) {
  for (const node of nodes) {
    visit(node);
    walk(node.children, visit);
  }
}

export function collectWbsAssignees(nodes: WBSNode[]): FilterOption[] {
  const map = new Map<number, string>();
  walk(nodes, (node) => {
    if (node.assignee_id != null) {
      map.set(node.assignee_id, node.assignee_name ?? `User #${node.assignee_id}`);
    }
  });
  return [...map.entries()]
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name, "ru"));
}

export function collectWbsStatuses(nodes: WBSNode[]): FilterOption[] {
  const map = new Map<number, string>();
  walk(nodes, (node) => {
    if (node.workflow_status_id != null) {
      map.set(
        node.workflow_status_id,
        node.workflow_status_name ?? `Status #${node.workflow_status_id}`,
      );
    }
  });
  return [...map.entries()]
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name, "ru"));
}
