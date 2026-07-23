import { useEffect, useRef } from "react";
import BpmnJS from "bpmn-js/lib/NavigatedViewer";
import "bpmn-js/dist/assets/diagram-js.css";
import "bpmn-js/dist/assets/bpmn-js.css";
import "bpmn-js/dist/assets/bpmn-font/css/bpmn.css";

type Props = {
  xml: string;
  height?: number;
};

export function BpmnViewer({ xml, height = 360 }: Props) {
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
      const canvas = viewer.get("canvas") as { zoom: (mode: string) => void };
      canvas.zoom("fit-viewport");
    });
  }, [xml]);

  return (
    <div
      ref={containerRef}
      className="overflow-hidden rounded-lg border border-border bg-cream"
      style={{ height }}
    />
  );
}
