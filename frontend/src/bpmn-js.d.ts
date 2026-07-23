declare module "bpmn-js/lib/NavigatedViewer" {
  export default class NavigatedViewer {
    constructor(options: { container: HTMLElement });
    importXML(xml: string): Promise<unknown>;
    get(name: string): unknown;
    destroy(): void;
  }
}

declare module "bpmn-js/dist/assets/diagram-js.css";
declare module "bpmn-js/dist/assets/bpmn-js.css";
declare module "bpmn-js/dist/assets/bpmn-font/css/bpmn.css";
