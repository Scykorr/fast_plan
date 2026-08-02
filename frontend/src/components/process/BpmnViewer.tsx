import { useEffect, useRef, useState } from "react";
import BpmnJS from "bpmn-js/lib/NavigatedViewer";
import "bpmn-js/dist/assets/diagram-js.css";
import "bpmn-js/dist/assets/bpmn-js.css";
import "bpmn-js/dist/assets/bpmn-font/css/bpmn.css";

import { TermHint } from "../TermHint";

type Props = {
  xml: string;
  height?: number;
  /** BPMN element ids with active tokens (highlighted). */
  activeElementIds?: string[];
  /** Extra element ids to outline (e.g. SubProcess of selected child). */
  highlightElementIds?: string[];
};

type SubProcessInfo = { id: string; name: string };

function listSubProcesses(viewer: BpmnJS): SubProcessInfo[] {
  const registry = viewer.get("elementRegistry") as {
    filter: (fn: (el: { id: string; type?: string; businessObject?: { name?: string } }) => boolean) => Array<{
      id: string;
      businessObject?: { name?: string };
    }>;
  };
  return registry
    .filter((el) => el.type === "bpmn:SubProcess")
    .map((el) => ({
      id: el.id,
      name: el.businessObject?.name || el.id,
    }));
}

function setChildrenVisible(
  viewer: BpmnJS,
  subProcessId: string,
  visible: boolean,
) {
  const registry = viewer.get("elementRegistry") as {
    filter: (fn: (el: { id: string; parent?: { id?: string } }) => boolean) => Array<{
      id: string;
    }>;
  };
  const canvas = viewer.get("canvas") as {
    getGraphics: (el: { id: string } | string) => SVGElement | undefined;
  };
  const children = registry.filter((el) => el.parent?.id === subProcessId);
  for (const child of children) {
    const gfx = canvas.getGraphics(child);
    if (gfx) {
      gfx.style.display = visible ? "" : "none";
    }
  }
}

export function BpmnViewer({
  xml,
  height = 360,
  activeElementIds = [],
  highlightElementIds = [],
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<BpmnJS | null>(null);
  const [subProcesses, setSubProcesses] = useState<SubProcessInfo[]>([]);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }
    const viewer = new BpmnJS({ container: containerRef.current });
    viewerRef.current = viewer;
    return () => {
      viewer.destroy();
      viewerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !xml.trim()) {
      return;
    }
    void viewer.importXML(xml).then(() => {
      const canvas = viewer.get("canvas") as {
        zoom: (mode: string) => void;
        addMarker: (id: string, className: string) => void;
        removeMarker: (id: string, className: string) => void;
      };
      canvas.zoom("fit-viewport");
      const found = listSubProcesses(viewer);
      setSubProcesses(found);
      setCollapsed(new Set());
      for (const id of activeElementIds) {
        try {
          canvas.addMarker(id, "fp-token-highlight");
        } catch {
          /* element may be missing from diagram */
        }
      }
      for (const id of highlightElementIds) {
        try {
          canvas.addMarker(id, "fp-subprocess-highlight");
        } catch {
          /* ignore */
        }
      }
    });
  }, [xml, activeElementIds, highlightElementIds]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || subProcesses.length === 0) {
      return;
    }
    for (const sp of subProcesses) {
      setChildrenVisible(viewer, sp.id, !collapsed.has(sp.id));
      const canvas = viewer.get("canvas") as {
        addMarker: (id: string, className: string) => void;
        removeMarker: (id: string, className: string) => void;
      };
      try {
        if (collapsed.has(sp.id)) {
          canvas.addMarker(sp.id, "fp-subprocess-collapsed");
        } else {
          canvas.removeMarker(sp.id, "fp-subprocess-collapsed");
        }
      } catch {
        /* ignore */
      }
    }
  }, [collapsed, subProcesses]);

  const toggleCollapse = (id: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="space-y-2">
      {subProcesses.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
          <span>
            <TermHint term="subprocess">SubProcess</TermHint>:
          </span>
          {subProcesses.map((sp) => (
            <button
              key={sp.id}
              type="button"
              className="rounded border border-border px-2 py-0.5 hover:bg-cream"
              onClick={() => toggleCollapse(sp.id)}
              title={collapsed.has(sp.id) ? "Развернуть содержимое" : "Свернуть содержимое"}
            >
              {collapsed.has(sp.id) ? "▸" : "▾"} {sp.name}
            </button>
          ))}
        </div>
      )}
      <div
        ref={containerRef}
        className="fp-bpmn-viewer overflow-hidden rounded-lg border border-border bg-cream"
        style={{ height }}
      />
    </div>
  );
}
