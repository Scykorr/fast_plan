import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { WBSNode } from "../../api/projects";
import {
  buildMindMapGraph,
  findWBSNode,
  getAncestorPath,
  type ColorMode,
  type WBSFlowNodeData,
} from "./wbs/buildMindMap";
import { WBSMindMapNode } from "./wbs/WBSMindMapNode";
import {
  computeWBSMove,
  findIntersectingNodeIds,
  pickDropTargetId,
} from "./wbs/wbsDragDrop";

const nodeTypes = { wbsNode: WBSMindMapNode };

type ContextMenuState = {
  x: number;
  y: number;
  node: WBSNode;
} | null;

type WBSTreeViewProps = {
  nodes: WBSNode[];
  onAddChild: (parentId: number) => void;
  onAddSibling?: (parentId: number) => void;
  onDelete: (nodeId: number) => void;
  onRename?: (nodeId: number, title: string) => void;
  onMove?: (nodeId: number, parentId: number, position: number) => void;
  selectedId?: number | null;
  onSelect?: (node: WBSNode) => void;
};

export function WBSTreeView({
  nodes,
  onAddChild,
  onAddSibling,
  onDelete,
  onRename,
  onMove,
  selectedId = null,
  onSelect,
}: WBSTreeViewProps) {
  const [colorMode, setColorMode] = useState<ColorMode>("progress");
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());
  const [focusRootId, setFocusRootId] = useState<number | null>(null);
  const [contextMenu, setContextMenu] = useState<ContextMenuState>(null);
  const [dropTargetId, setDropTargetId] = useState<number | null>(null);
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const displayRoots = useMemo(() => {
    if (focusRootId === null) {
      return nodes;
    }
    const focused = findWBSNode(nodes, focusRootId);
    return focused ? [focused] : nodes;
  }, [nodes, focusRootId]);

  const breadcrumb = useMemo(() => {
    if (focusRootId === null) {
      return [];
    }
    return getAncestorPath(nodes, focusRootId);
  }, [nodes, focusRootId]);

  const graph = useMemo(
    () =>
      buildMindMapGraph(
        displayRoots,
        collapsed,
        selectedId,
        colorMode,
        dropTargetId,
        draggingId,
      ),
    [displayRoots, collapsed, selectedId, colorMode, dropTargetId, draggingId],
  );

  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState(graph.nodes);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState(graph.edges);

  useEffect(() => {
    if (draggingId !== null) {
      return;
    }
    setFlowNodes(graph.nodes);
    setFlowEdges(graph.edges);
  }, [graph, draggingId, setFlowNodes, setFlowEdges]);

  useEffect(() => {
    if (draggingId === null) {
      return;
    }
    setFlowNodes((current) =>
      current.map((node) => ({
        ...node,
        data: {
          ...(node.data as WBSFlowNodeData),
          isDropTarget: Number(node.id) === dropTargetId,
          isDragging: Number(node.id) === draggingId,
        },
      })),
    );
  }, [dropTargetId, draggingId]);

  const toggleCollapse = useCallback((nodeId: number) => {
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, []);

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node<WBSFlowNodeData>) => {
      setContextMenu(null);
      onSelect?.(node.data.wbsNode);
    },
    [onSelect],
  );

  const handleNodeContextMenu = useCallback(
    (event: React.MouseEvent, node: Node<WBSFlowNodeData>) => {
      event.preventDefault();
      onSelect?.(node.data.wbsNode);
      setContextMenu({
        x: event.clientX,
        y: event.clientY,
        node: node.data.wbsNode,
      });
    },
    [onSelect],
  );

  const handleNodeDragStart = useCallback(
    (event: MouseEvent | TouchEvent, node: Node<WBSFlowNodeData>) => {
      void event;
      setDraggingId(Number(node.id));
      setDropTargetId(null);
      setContextMenu(null);
    },
    [],
  );

  const handleNodeDrag = useCallback(
    (event: MouseEvent | TouchEvent, draggedNode: Node<WBSFlowNodeData>) => {
      void event;
      setFlowNodes((current) => {
        const nodesWithDragged = current.map((node) =>
          node.id === draggedNode.id ? draggedNode : node,
        );
        const intersections = findIntersectingNodeIds(draggedNode, nodesWithDragged);
        const targetId = pickDropTargetId(
          draggedNode.data.wbsNode,
          intersections,
          nodes,
        );
        setDropTargetId(targetId);
        return nodesWithDragged;
      });
    },
    [nodes, setFlowNodes],
  );

  const handleNodeDragStop = useCallback(
    (event: MouseEvent | TouchEvent, draggedNode: Node<WBSFlowNodeData>) => {
      void event;
      setFlowNodes((current) => {
        const nodesWithDragged = current.map((node) =>
          node.id === draggedNode.id ? draggedNode : node,
        );
        const intersections = findIntersectingNodeIds(draggedNode, nodesWithDragged);
        const positions = new Map(
          nodesWithDragged.map((node) => [Number(node.id), node.position]),
        );
        const action = computeWBSMove(
          draggedNode.data.wbsNode,
          intersections,
          positions,
          nodes,
        );

        if (action && onMove) {
          onMove(draggedNode.data.wbsNode.id, action.parentId, action.position);
          if (action.parentId !== draggedNode.data.wbsNode.parent_id) {
            setCollapsed((current) => {
              const next = new Set(current);
              next.delete(action.parentId);
              return next;
            });
          }
        }

        return nodesWithDragged;
      });
      setDraggingId(null);
      setDropTargetId(null);
    },
    [nodes, onMove, setFlowNodes],
  );

  useEffect(() => {
    const closeMenu = () => setContextMenu(null);
    window.addEventListener("click", closeMenu);
    return () => window.removeEventListener("click", closeMenu);
  }, []);

  if (nodes.length === 0) {
    return <p className="text-sm text-text-muted">WBS пуст</p>;
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-text">
          <span className="text-text-muted">Цвет по:</span>
          <select
            value={colorMode}
            onChange={(event) => setColorMode(event.target.value as ColorMode)}
            className="rounded-lg border border-border bg-surface px-2 py-1 text-sm"
          >
            <option value="progress">Прогрессу</option>
            <option value="type">Типу узла</option>
          </select>
        </label>
        {breadcrumb.length > 0 && (
          <div className="flex flex-wrap items-center gap-1 text-sm">
            <button
              type="button"
              onClick={() => setFocusRootId(null)}
              className="text-primary hover:underline"
            >
              Весь проект
            </button>
            {breadcrumb.map((item, index) => (
              <span key={item.id} className="flex items-center gap-1 text-text-muted">
                <span>/</span>
                {index === breadcrumb.length - 1 ? (
                  <span className="font-medium text-text">{item.title}</span>
                ) : (
                  <button
                    type="button"
                    onClick={() => setFocusRootId(item.id)}
                    className="text-primary hover:underline"
                  >
                    {item.code}
                  </button>
                )}
              </span>
            ))}
          </div>
        )}
        <p className="text-xs text-text-muted">
          Перетащите узел на другой — станет дочерним · Между соседями — выше/ниже ·
          ПКМ — меню · Двойной клик — свернуть
        </p>
      </div>

      <div className="h-[560px] overflow-hidden rounded-xl border border-border bg-cream/40">
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          onNodeClick={handleNodeClick}
          onNodeContextMenu={handleNodeContextMenu}
          onNodeDoubleClick={(_event, node) => {
            if (node.data.hasChildren) {
              toggleCollapse(node.data.wbsNode.id);
            }
          }}
          onNodeDragStart={handleNodeDragStart}
          onNodeDrag={handleNodeDrag}
          onNodeDragStop={handleNodeDragStop}
          fitView
          minZoom={0.25}
          maxZoom={1.75}
          nodesDraggable={Boolean(onMove)}
          nodesConnectable={false}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#E8E2D9" gap={20} />
          <Controls showInteractive={false} />
          <MiniMap
            nodeColor={(node) => {
              const data = node.data as WBSFlowNodeData;
              return data.wbsNode ? "#C45C3E" : "#E8E2D9";
            }}
            maskColor="rgba(250, 247, 242, 0.75)"
          />
        </ReactFlow>
      </div>

      {contextMenu && (
        <div
          className="fixed z-50 min-w-44 rounded-lg border border-border bg-surface py-1 shadow-lg"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(event) => event.stopPropagation()}
        >
          <button
            type="button"
            className="block w-full px-3 py-2 text-left text-sm hover:bg-cream"
            onClick={() => onAddChild(contextMenu.node.id)}
          >
            + Дочерний узел
          </button>
          {onRename && (
            <button
              type="button"
              className="block w-full px-3 py-2 text-left text-sm hover:bg-cream"
              onClick={() => {
                const title = window.prompt("Название узла", contextMenu.node.title);
                if (title?.trim() && title.trim() !== contextMenu.node.title) {
                  onRename(contextMenu.node.id, title.trim());
                }
              }}
            >
              Переименовать
            </button>
          )}
          {contextMenu.node.parent_id && onAddSibling && (
            <button
              type="button"
              className="block w-full px-3 py-2 text-left text-sm hover:bg-cream"
              onClick={() => onAddSibling(contextMenu.node.parent_id!)}
            >
              + Соседний узел
            </button>
          )}
          {contextMenu.node.children.length > 0 && (
            <button
              type="button"
              className="block w-full px-3 py-2 text-left text-sm hover:bg-cream"
              onClick={() => toggleCollapse(contextMenu.node.id)}
            >
              {collapsed.has(contextMenu.node.id) ? "Развернуть" : "Свернуть"}
            </button>
          )}
          <button
            type="button"
            className="block w-full px-3 py-2 text-left text-sm hover:bg-cream"
            onClick={() => setFocusRootId(contextMenu.node.id)}
          >
            Фокус на ветке
          </button>
          {contextMenu.node.parent_id && (
            <button
              type="button"
              className="block w-full px-3 py-2 text-left text-sm text-primary hover:bg-cream"
              onClick={() => onDelete(contextMenu.node.id)}
            >
              Удалить
            </button>
          )}
        </div>
      )}
    </div>
  );
}
