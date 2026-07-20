import dagre from "@dagrejs/dagre";
import { useMemo } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { PertNetwork } from "../../api/projects";

type PertNodeData = {
  label: string;
  code: string;
  optimistic: number;
  mostLikely: number;
  pessimistic: number;
  expected: number;
  isCritical: boolean;
};

const NODE_WIDTH = 200;
const NODE_HEIGHT = 88;

function PertFlowNode({ data }: { data: PertNodeData }) {
  return (
    <div
      className={[
        "rounded-lg border px-3 py-2 text-xs shadow-sm",
        data.isCritical
          ? "border-primary bg-primary/10"
          : "border-border bg-surface",
      ].join(" ")}
    >
      <p className="truncate font-semibold text-text">
        {data.code} {data.label}
      </p>
      <p className="mt-1 text-text-muted">
        O/M/P: {data.optimistic}/{data.mostLikely}/{data.pessimistic}
      </p>
      <p className="font-medium text-secondary">E = {data.expected} дн.</p>
    </div>
  );
}

const nodeTypes = { pertNode: PertFlowNode };

function layoutPert(network: PertNetwork): {
  nodes: Node<PertNodeData>[];
  edges: Edge[];
} {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "LR", nodesep: 40, ranksep: 60 });

  for (const node of network.nodes) {
    graph.setNode(String(node.id), { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const edge of network.edges) {
    graph.setEdge(String(edge.from), String(edge.to));
  }
  dagre.layout(graph);

  const nodes: Node<PertNodeData>[] = network.nodes.map((node) => {
    const layout = graph.node(String(node.id));
    return {
      id: String(node.id),
      type: "pertNode",
      position: {
        x: layout.x - NODE_WIDTH / 2,
        y: layout.y - NODE_HEIGHT / 2,
      },
      data: {
        label: node.name,
        code: node.code,
        optimistic: node.optimistic_days,
        mostLikely: node.most_likely_days,
        pessimistic: node.pessimistic_days,
        expected: node.expected_days,
        isCritical: node.is_critical,
      },
    };
  });

  const edges: Edge[] = network.edges.map((edge) => ({
    id: String(edge.id),
    source: String(edge.from),
    target: String(edge.to),
    label: edge.lag_days ? `+${edge.lag_days}d` : edge.type,
    animated: network.critical_path_ids.includes(edge.from),
  }));

  return { nodes, edges };
}

type Props = {
  network: PertNetwork;
};

export function PertDiagram({ network }: Props) {
  const { nodes, edges } = useMemo(() => layoutPert(network), [network]);

  if (network.nodes.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        Нет активностей для построения PERT-диаграммы.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-text-muted">
        Длительность проекта (CPM): {network.project_duration} дн. · узлов:{" "}
        {network.nodes.length}
      </p>
      <div className="h-[520px] rounded-xl border border-border bg-surface">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          proOptions={{ hideAttribution: true }}
        >
          <Background />
          <Controls showInteractive={false} />
          <MiniMap pannable zoomable />
        </ReactFlow>
      </div>
    </div>
  );
}
