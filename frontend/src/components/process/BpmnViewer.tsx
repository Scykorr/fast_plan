import { useEffect, useRef } from "react";
import BpmnJS from "bpmn-js/lib/NavigatedViewer";
import "bpmn-js/dist/assets/diagram-js.css";
import "bpmn-js/dist/assets/bpmn-js.css";
import "bpmn-js/dist/assets/bpmn-font/css/bpmn.css";

type Props = {
  xml: string;
  height?: number;
  /** BPMN element ids with active tokens (highlighted). */
  activeElementIds?: string[];
};

export function BpmnViewer({ xml, height = 360, activeElementIds = [] }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<BpmnJS | null>(null);

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
      for (const id of activeElementIds) {
        try {
          canvas.addMarker(id, "fp-token-highlight");
        } catch {
          /* element may be missing from diagram */
        }
      }
    });
  }, [xml, activeElementIds]);

  return (
    <div
      ref={containerRef}
      className="fp-bpmn-viewer overflow-hidden rounded-lg border border-border bg-cream"
      style={{ height }}
    />
  );
}
