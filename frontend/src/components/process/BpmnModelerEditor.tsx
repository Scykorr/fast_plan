import { useEffect, useRef } from "react";
import BpmnModeler from "bpmn-js/lib/Modeler";
import "bpmn-js/dist/assets/diagram-js.css";
import "bpmn-js/dist/assets/bpmn-js.css";
import "bpmn-js/dist/assets/bpmn-font/css/bpmn.css";
import "bpmn-js/dist/assets/bpmn-font/css/bpmn-embedded.css";

type Props = {
  xml: string;
  height?: number;
  onChange?: (xml: string) => void;
};

export function BpmnModelerEditor({ xml, height = 420, onChange }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const modelerRef = useRef<BpmnModeler | null>(null);
  const onChangeRef = useRef(onChange);
  const suppressImportRef = useRef(false);
  const lastXmlRef = useRef("");
  onChangeRef.current = onChange;

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }
    const modeler = new BpmnModeler({ container: containerRef.current });
    modelerRef.current = modeler;
    const eventBus = modeler.get("eventBus") as {
      on: (event: string, cb: () => void) => void;
    };
    const emitXml = () => {
      void modeler
        .saveXML({ format: true })
        .then(({ xml: next }) => {
          if (!next || !onChangeRef.current) {
            return;
          }
          suppressImportRef.current = true;
          lastXmlRef.current = next;
          onChangeRef.current(next);
        })
        .catch(() => undefined);
    };
    eventBus.on("commandStack.changed", emitXml);
    return () => {
      modeler.destroy();
      modelerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const modeler = modelerRef.current;
    if (!modeler || !xml.trim()) {
      return;
    }
    if (suppressImportRef.current) {
      suppressImportRef.current = false;
      return;
    }
    if (xml === lastXmlRef.current) {
      return;
    }
    lastXmlRef.current = xml;
    void modeler
      .importXML(xml)
      .then(() => {
        const canvas = modeler.get("canvas") as { zoom: (mode: string) => void };
        canvas.zoom("fit-viewport");
      })
      .catch(() => undefined);
  }, [xml]);

  return (
    <div
      ref={containerRef}
      className="overflow-hidden rounded-lg border border-border bg-cream"
      style={{ height }}
    />
  );
}
