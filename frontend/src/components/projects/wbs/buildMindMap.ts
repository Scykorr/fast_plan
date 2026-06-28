import dagre from "@dagrejs/dagre";
import type { Edge, Node } from "@xyflow/react";

import type { WBSNode } from "../../../api/projects";

export type ColorMode = "progress" | "type";

export type WBSFlowNodeData = {
  wbsNode: WBSNode;
  colorMode: ColorMode;
  isSelected: boolean;
  isCollapsed: boolean;
  hasChildren: boolean;
  isDropTarget: boolean;
  isDragging: boolean;
};

const NODE_WIDTH = 232;
const NODE_HEIGHT = 76;

export { NODE_WIDTH, NODE_HEIGHT };

function flattenVisible(
  nodes: WBSNode[],
  collapsed: Set<number>,
  parentCollapsed = false,
): WBSNode[] {
  const result: WBSNode[] = [];
  for (const node of nodes) {
    if (parentCollapsed) {
      continue;
    }
    result.push(node);
    const hideChildren = collapsed.has(node.id);
    result.push(...flattenVisible(node.children, collapsed, hideChildren));
  }
  return result;
}

export function getNodeColor(node: WBSNode, colorMode: ColorMode): string {
  if (colorMode === "type") {
    if (node.node_type === "milestone") {
      return "#E8A838";
    }
    if (node.node_type === "deliverable") {
      return "#6B8F71";
    }
    return "#C45C3E";
  }

  const progress = node.schedule?.progress ?? 0;
  if (progress >= 100) {
    return "#6B8F71";
  }
  if (progress > 0) {
    return "#E8A838";
  }
  return "#C45C3E";
}

export function buildMindMapGraph(
  roots: WBSNode[],
  collapsed: Set<number>,
  selectedId: number | null,
  colorMode: ColorMode,
  dropTargetId: number | null = null,
  draggingId: number | null = null,
): { nodes: Node<WBSFlowNodeData>[]; edges: Edge[] } {
  const visible = flattenVisible(roots, collapsed);
  const visibleIds = new Set(visible.map((node) => node.id));

  const flowNodes: Node<WBSFlowNodeData>[] = visible.map((node) => ({
    id: String(node.id),
    type: "wbsNode",
    draggable: node.parent_id !== null,
    data: {
      wbsNode: node,
      colorMode,
      isSelected: selectedId === node.id,
      isCollapsed: collapsed.has(node.id),
      hasChildren: node.children.length > 0,
      isDropTarget: dropTargetId === node.id,
      isDragging: draggingId === node.id,
    },
    position: { x: 0, y: 0 },
  }));

  const flowEdges: Edge[] = [];
  for (const node of visible) {
    if (node.parent_id && visibleIds.has(node.parent_id)) {
      flowEdges.push({
        id: `e-${node.parent_id}-${node.id}`,
        source: String(node.parent_id),
        target: String(node.id),
        type: "smoothstep",
        style: { stroke: "#E8E2D9", strokeWidth: 2 },
      });
    }
  }

  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "LR", nodesep: 48, ranksep: 72, marginx: 24, marginy: 24 });

  flowNodes.forEach((node) => {
    graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });
  flowEdges.forEach((edge) => {
    graph.setEdge(edge.source, edge.target);
  });

  dagre.layout(graph);

  const positionedNodes = flowNodes.map((node) => {
    const layout = graph.node(node.id);
    return {
      ...node,
      position: {
        x: layout.x - NODE_WIDTH / 2,
        y: layout.y - NODE_HEIGHT / 2,
      },
    };
  });

  return { nodes: positionedNodes, edges: flowEdges };
}

export function findWBSNode(nodes: WBSNode[], id: number): WBSNode | null {
  for (const node of nodes) {
    if (node.id === id) {
      return node;
    }
    const found = findWBSNode(node.children, id);
    if (found) {
      return found;
    }
  }
  return null;
}

export function getAncestorPath(nodes: WBSNode[], id: number): WBSNode[] {
  const path: WBSNode[] = [];
  function walk(list: WBSNode[], trail: WBSNode[]): boolean {
    for (const node of list) {
      const next = [...trail, node];
      if (node.id === id) {
        path.push(...next);
        return true;
      }
      if (walk(node.children, next)) {
        return true;
      }
    }
    return false;
  }
  walk(nodes, []);
  return path;
}
