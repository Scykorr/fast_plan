import type { WBSNode } from "../../api/projects";

type WBSTreeViewProps = {
  nodes: WBSNode[];
  onAddChild: (parentId: number) => void;
  onDelete: (nodeId: number) => void;
  selectedId?: number | null;
  onSelect?: (node: WBSNode) => void;
};

function WBSNodeItem({
  node,
  onAddChild,
  onDelete,
  selectedId,
  onSelect,
  level = 0,
}: {
  node: WBSNode;
  onAddChild: (parentId: number) => void;
  onDelete: (nodeId: number) => void;
  selectedId?: number | null;
  onSelect?: (node: WBSNode) => void;
  level?: number;
}) {
  const isSelected = selectedId === node.id;
  const isRoot = node.parent_id === null;

  return (
    <li>
      <div
        className={[
          "flex items-center justify-between rounded-lg border px-3 py-2",
          isSelected
            ? "border-primary bg-cream"
            : "border-border bg-surface",
        ].join(" ")}
        style={{ marginLeft: level * 16 }}
      >
        <button
          type="button"
          onClick={() => onSelect?.(node)}
          className="flex flex-1 items-center gap-2 text-left"
        >
          <span className="text-xs font-mono text-text-muted">{node.code}</span>
          <span className="text-sm font-medium text-text">{node.title}</span>
          <span className="rounded-full bg-secondary/15 px-2 py-0.5 text-xs text-secondary">
            {node.node_type}
          </span>
          {node.schedule && (
            <span className="text-xs text-text-muted">{node.schedule.progress}%</span>
          )}
        </button>
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => onAddChild(node.id)}
            className="rounded px-2 py-1 text-xs text-primary hover:bg-cream"
          >
            +
          </button>
          {!isRoot && (
            <button
              type="button"
              onClick={() => onDelete(node.id)}
              className="rounded px-2 py-1 text-xs text-text-muted hover:text-primary"
            >
              ×
            </button>
          )}
        </div>
      </div>
      {node.children.length > 0 && (
        <ul className="mt-2 space-y-2">
          {node.children.map((child) => (
            <WBSNodeItem
              key={child.id}
              node={child}
              onAddChild={onAddChild}
              onDelete={onDelete}
              selectedId={selectedId}
              onSelect={onSelect}
              level={level + 1}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

export function WBSTreeView({
  nodes,
  onAddChild,
  onDelete,
  selectedId,
  onSelect,
}: WBSTreeViewProps) {
  if (nodes.length === 0) {
    return <p className="text-sm text-text-muted">WBS пуст</p>;
  }

  return (
    <ul className="space-y-2">
      {nodes.map((node) => (
        <WBSNodeItem
          key={node.id}
          node={node}
          onAddChild={onAddChild}
          onDelete={onDelete}
          selectedId={selectedId}
          onSelect={onSelect}
        />
      ))}
    </ul>
  );
}
