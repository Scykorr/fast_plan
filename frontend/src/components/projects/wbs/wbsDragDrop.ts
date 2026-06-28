import type { WBSNode } from "../../../api/projects";
import { findWBSNode, NODE_HEIGHT, NODE_WIDTH } from "./buildMindMap";

export type WBSMoveAction = {
  parentId: number;
  position: number;
};

export function findIntersectingNodeIds(
  dragged: { id: string; position: { x: number; y: number } },
  nodes: Array<{ id: string; position: { x: number; y: number } }>,
): string[] {
  return nodes
    .filter((node) => node.id !== dragged.id)
    .filter((node) => {
      const ax = dragged.position.x;
      const ay = dragged.position.y;
      const bx = node.position.x;
      const by = node.position.y;
      return (
        ax < bx + NODE_WIDTH &&
        ax + NODE_WIDTH > bx &&
        ay < by + NODE_HEIGHT &&
        ay + NODE_HEIGHT > by
      );
    })
    .map((node) => node.id);
}

export function pickDropTargetId(
  dragged: WBSNode,
  intersectingNodeIds: string[],
  treeRoots: WBSNode[],
): number | null {
  for (const idStr of intersectingNodeIds) {
    const targetId = Number(idStr);
    if (targetId === dragged.id) {
      continue;
    }
    const target = findWBSNode(treeRoots, targetId);
    if (!target) {
      continue;
    }
    if (isDescendantOf(dragged, targetId)) {
      continue;
    }
    return targetId;
  }
  return null;
}

export function isDescendantOf(ancestor: WBSNode, nodeId: number): boolean {
  for (const child of ancestor.children) {
    if (child.id === nodeId) {
      return true;
    }
    if (isDescendantOf(child, nodeId)) {
      return true;
    }
  }
  return false;
}

export function getSiblings(nodes: WBSNode[], parentId: number): WBSNode[] {
  const parent = findWBSNode(nodes, parentId);
  return parent?.children ?? [];
}

export function computeWBSMove(
  dragged: WBSNode,
  intersectingNodeIds: string[],
  flowPositions: Map<number, { x: number; y: number }>,
  treeRoots: WBSNode[],
): WBSMoveAction | null {
  if (dragged.parent_id === null) {
    return null;
  }

  for (const idStr of intersectingNodeIds) {
    const targetId = Number(idStr);
    if (targetId === dragged.id) {
      continue;
    }
    const target = findWBSNode(treeRoots, targetId);
    if (!target) {
      continue;
    }
    if (isDescendantOf(dragged, targetId)) {
      continue;
    }

    const position = target.children.filter((child) => child.id !== dragged.id).length;
    if (targetId === dragged.parent_id && position === dragged.position) {
      return null;
    }
    return { parentId: targetId, position };
  }

  if (intersectingNodeIds.length > 0) {
    return null;
  }

  const parentId = dragged.parent_id;
  const siblings = getSiblings(treeRoots, parentId).filter(
    (sibling) => sibling.id !== dragged.id,
  );
  const draggedY = flowPositions.get(dragged.id)?.y ?? 0;

  let position = 0;
  for (const sibling of siblings) {
    const siblingY = flowPositions.get(sibling.id)?.y ?? 0;
    if (draggedY > siblingY) {
      position += 1;
    }
  }

  if (position === dragged.position) {
    return null;
  }

  return { parentId, position };
}
