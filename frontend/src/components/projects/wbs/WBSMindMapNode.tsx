import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { memo } from "react";

import type { WBSFlowNodeData } from "./buildMindMap";
import { getNodeColor } from "./buildMindMap";

function WBSMindMapNodeComponent({ data }: NodeProps<Node<WBSFlowNodeData>>) {
  const { wbsNode, colorMode, isSelected, isCollapsed, hasChildren, isDropTarget, isDragging } =
    data;
  const accent = getNodeColor(wbsNode, colorMode);
  const progress = wbsNode.schedule?.progress ?? 0;

  return (
    <div
      data-testid={`wbs-node-${wbsNode.id}`}
      className={[
        "w-[232px] rounded-xl border-2 bg-surface shadow-sm transition-shadow",
        isSelected ? "border-primary shadow-md" : "border-border",
        isDropTarget ? "ring-2 ring-primary ring-offset-2" : "",
        isDragging ? "opacity-70" : "",
      ].join(" ")}
      style={{ borderTopColor: accent, borderTopWidth: 4 }}
    >
      <Handle type="target" position={Position.Left} className="!bg-border !w-2 !h-2" />
      <div className="px-3 py-2">
        <div className="flex items-start justify-between gap-2">
          <span className="font-mono text-[10px] text-text-muted">{wbsNode.code}</span>
          {hasChildren && (
            <span className="text-[10px] text-text-muted">
              {isCollapsed ? "▶" : "▼"}
            </span>
          )}
        </div>
        <p className="mt-0.5 line-clamp-2 text-sm font-semibold leading-tight text-text">
          {wbsNode.title}
        </p>
        {wbsNode.capacity_hint?.overloaded && (
          <p className="mt-1 text-[10px] font-medium text-[#c45c26]">
            Перегруз · {Math.round((wbsNode.capacity_hint.utilization ?? 0) * 100)}%
          </p>
        )}
        {wbsNode.quality && wbsNode.quality.total > 0 && (
          <p
            className={[
              "mt-1 text-[10px] font-medium",
              wbsNode.quality.failed > 0
                ? "text-[#c45c26]"
                : wbsNode.quality.open > 0
                  ? "text-text-muted"
                  : "text-primary",
            ].join(" ")}
          >
            QA {wbsNode.quality.passed}/{wbsNode.quality.total}
            {wbsNode.quality.failed > 0 ? ` · fail ${wbsNode.quality.failed}` : ""}
          </p>
        )}
        {(wbsNode.org_unit_name || wbsNode.obs_role_name) && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {wbsNode.org_unit_name && (
              <span className="rounded-md bg-cream px-1.5 py-0.5 text-[10px] font-medium text-text">
                {wbsNode.org_unit_name}
              </span>
            )}
            {wbsNode.obs_role_name && (
              <span className="rounded-md border border-border px-1.5 py-0.5 text-[10px] text-text-muted">
                {wbsNode.obs_role_name}
              </span>
            )}
          </div>
        )}
        <div className="mt-2 flex items-center justify-between gap-2 text-[10px] text-text-muted">
          <span className="capitalize">{wbsNode.node_type.replace("_", " ")}</span>
          {wbsNode.schedule && <span>{progress}%</span>}
        </div>
        {wbsNode.schedule && (
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-cream">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${progress}%`, backgroundColor: accent }}
            />
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-border !w-2 !h-2" />
    </div>
  );
}

export const WBSMindMapNode = memo(WBSMindMapNodeComponent);
