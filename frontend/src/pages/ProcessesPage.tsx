import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { parseApiError } from "../api/errors";
import type {
  CaseDefinition,
  CaseInstance,
  DecisionDefinition,
  ProcessAdapterCatalog,
  ProcessDefinition,
  ProcessInstance,
  ProcessMetrics,
  ProcessMining,
  ProcessOps,
  ProcessPack,
} from "../api/process";
import { BpmnModelerEditor } from "../components/process/BpmnModelerEditor";
import { BpmnViewer } from "../components/process/BpmnViewer";
import { ProcessWorkTree } from "../components/process/ProcessWorkTree";
import { ErrorMessage } from "../components/ErrorMessage";
import { GlossaryText } from "../components/TermHint";
import type { ProcessWorkNode } from "../api/process";
import { useProcessApi } from "../hooks/useProcessApi";
import { useWorkspace } from "../context/WorkspaceContext";

const EMPTY_BPMN = `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
  id="Defs_new" targetNamespace="http://fastplan.local/bpmn">
  <bpmn:process id="NewProcess" name="New process" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1" name="Start">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:userTask id="Activity_1" name="Review">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:endEvent id="EndEvent_1" name="End">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Activity_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Activity_1" targetRef="EndEvent_1" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="NewProcess">
      <bpmndi:BPMNShape id="StartEvent_1_di" bpmnElement="StartEvent_1">
        <dc:Bounds x="152" y="102" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_1_di" bpmnElement="Activity_1">
        <dc:Bounds x="240" y="80" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EndEvent_1_di" bpmnElement="EndEvent_1">
        <dc:Bounds x="392" y="102" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">
        <di:waypoint x="188" y="120" />
        <di:waypoint x="240" y="120" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_2_di" bpmnElement="Flow_2">
        <di:waypoint x="340" y="120" />
        <di:waypoint x="392" y="120" />
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>`;

export function ProcessesPage() {
  const api = useProcessApi();
  const { workspaceEpoch } = useWorkspace();
  const [definitions, setDefinitions] = useState<ProcessDefinition[]>([]);
  const [instances, setInstances] = useState<ProcessInstance[]>([]);
  const [packs, setPacks] = useState<ProcessPack[]>([]);
  const [metrics, setMetrics] = useState<ProcessMetrics | null>(null);
  const [ops, setOps] = useState<ProcessOps | null>(null);
  const [adapterCatalog, setAdapterCatalog] =
    useState<ProcessAdapterCatalog | null>(null);
  const [mining, setMining] = useState<ProcessMining | null>(null);
  const [cases, setCases] = useState<CaseInstance[]>([]);
  const [caseDefs, setCaseDefs] = useState<CaseDefinition[]>([]);
  const [decisions, setDecisions] = useState<DecisionDefinition[]>([]);
  const [dmnScore, setDmnScore] = useState("85");
  const [dmnResult, setDmnResult] = useState("");
  const [selected, setSelected] = useState<ProcessDefinition | null>(null);
  const [xmlDraft, setXmlDraft] = useState(EMPTY_BPMN);
  const [name, setName] = useState("Новый процесс");
  const [key, setKey] = useState("new-process");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showXml, setShowXml] = useState(false);
  const [migrateRunning, setMigrateRunning] = useState(false);
  const [instanceDetail, setInstanceDetail] = useState<{
    instance: ProcessInstance;
    children: ProcessInstance[];
    bpmn_xml: string;
    active_element_ids: string[];
    work_tree: ProcessWorkNode[];
  } | null>(null);
  const [highlightIds, setHighlightIds] = useState<string[]>([]);
  const [tab, setTab] = useState<
    | "defs"
    | "instances"
    | "packs"
    | "cases"
    | "dmn"
    | "ops"
    | "adapters"
    | "metrics"
  >("defs");

  const load = useCallback(async () => {
    if (!api) return;
    try {
      const [
        defs,
        inst,
        packList,
        m,
        opsData,
        mine,
        caseList,
        caseDefList,
        decisionList,
        adapters,
      ] = await Promise.all([
          api.listDefinitions(),
          api.listInstances(),
          api.listPacks(),
          api.metrics(),
          api.ops(),
          api.mining(),
          api.listCases(),
          api.listCaseDefinitions(),
          api.listDecisions(),
          api.adaptersCatalog(),
        ]);
      setDefinitions(defs);
      setInstances(inst);
      setPacks(packList);
      setMetrics(m);
      setOps(opsData);
      setMining(mine);
      setCases(caseList);
      setCaseDefs(caseDefList);
      setAdapterCatalog(adapters);
      setDecisions(decisionList);
    } catch (err) {
      setError(parseApiError(err));
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!api) return;
    setError("");
    try {
      const created = await api.createDefinition({
        key,
        name,
        bpmn_xml: xmlDraft,
        process_id: "NewProcess",
        description: "",
        category: "",
      });
      setMessage("Определение создано");
      setSelected(created);
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const handleSave = async () => {
    if (!api || !selected) return;
    try {
      const updated = await api.patchDefinition(selected.id, {
        name,
        bpmn_xml: xmlDraft,
      });
      setSelected(updated);
      setMessage("Сохранено (версия увеличена при смене XML)");
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">Процессы (BPMN)</h1>
        <p className="mt-1 text-sm text-text-muted">
          P8: BPMN 2.0 + SpiffWorkflow ·{" "}
          <Link to="/process-tasks" className="text-primary hover:underline">
            inbox задач
          </Link>
        </p>
      </div>

      <ErrorMessage message={error} />
      {message && (
        <p className="text-sm text-secondary" role="status">
          {message}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {(
          [
            ["defs", "Определения"],
            ["instances", "Инстансы"],
            ["packs", "Пакеты"],
            ["cases", "Кейсы CMMN"],
            ["dmn", "DMN"],
            ["ops", "Ops"],
            ["adapters", "Adapters"],
            ["metrics", "Метрики / Mining"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={[
              "rounded-lg border px-3 py-1.5 text-sm",
              tab === id
                ? "border-primary bg-cream text-primary"
                : "border-border text-text-muted hover:bg-cream",
            ].join(" ")}
          >
            <GlossaryText text={label} />
          </button>
        ))}
      </div>

      {tab === "defs" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-4 rounded-xl border border-border bg-surface p-4">
            <h2 className="font-semibold text-text">Каталог</h2>
            <ul className="max-h-64 space-y-2 overflow-y-auto text-sm">
              {definitions.map((d) => (
                <li key={d.id}>
                  <button
                    type="button"
                    className="w-full rounded-lg border border-border px-3 py-2 text-left hover:bg-cream"
                    onClick={() => {
                      setSelected(d);
                      setXmlDraft(d.bpmn_xml);
                      setName(d.name);
                      setKey(d.key);
                    }}
                  >
                    <span className="font-medium text-text">{d.name}</span>
                    <span className="ml-2 text-xs text-text-muted">
                      {d.key} · v{d.version}
                      {d.is_published ? " · published" : ""}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <form onSubmit={handleCreate} className="space-y-2 border-t border-border pt-4">
              <h3 className="text-sm font-semibold">Создать</h3>
              <input
                className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder="key"
                required
              />
              <input
                className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Название"
                required
              />
              <button
                type="submit"
                className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
              >
                Создать из шаблона XML
              </button>
            </form>
          </div>

          <div className="space-y-3 rounded-xl border border-border bg-surface p-4">
            <h2 className="font-semibold text-text">
              {selected ? selected.name : "Редактор BPMN"}
            </h2>
            <BpmnModelerEditor xml={xmlDraft} onChange={setXmlDraft} height={400} />
            <p className="rounded-lg border border-border bg-cream px-3 py-2 text-xs text-text-muted">
              <GlossaryText text="Inclusive Gateway" />: на исходящих sequenceFlow
              задайте условие (properties / conditionExpression) или default-flow.
              Join ждёт только взятые ветки. Пример-пак:{" "}
              <code className="text-[11px]">or_inclusive</code>.
            </p>
            <button
              type="button"
              className="text-xs text-primary hover:underline"
              onClick={() => setShowXml((v) => !v)}
            >
              {showXml ? "Скрыть XML" : "Показать XML"}
            </button>
            {showXml && (
              <textarea
                className="h-40 w-full rounded-lg border border-border bg-cream p-2 font-mono text-xs"
                value={xmlDraft}
                onChange={(e) => setXmlDraft(e.target.value)}
              />
            )}
            <div className="flex flex-wrap gap-2">
              {selected && (
                <>
                  <button
                    type="button"
                    className="rounded-lg bg-secondary px-3 py-1.5 text-sm font-semibold text-white"
                    onClick={() => void handleSave()}
                  >
                    Сохранить
                  </button>
                  <button
                    type="button"
                    className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
                    onClick={() =>
                      void (async () => {
                        if (!api || !selected) return;
                        try {
                          const published = await api.publish(selected.id, {
                            migrate_running: migrateRunning,
                          });
                          const mig = published.migration;
                          const migMsg =
                            migrateRunning && mig
                              ? ` · migrate ${mig.migrated_count}/${mig.prior_active_count} (skip ${mig.skipped_count})`
                              : mig && mig.prior_active_count > 0
                                ? ` · ${mig.prior_active_count} active на старых deployment (migrate off)`
                                : "";
                          setMessage(`Опубликовано${migMsg}`);
                          await load();
                        } catch (err) {
                          setError(parseApiError(err));
                        }
                      })()
                    }
                  >
                    Опубликовать
                  </button>
                  <label className="flex items-center gap-2 text-xs text-text-muted">
                    <input
                      type="checkbox"
                      checked={migrateRunning}
                      onChange={(e) => setMigrateRunning(e.target.checked)}
                    />
                    Migrate running instances
                  </label>
                  <button
                    type="button"
                    className="rounded-lg border border-border px-3 py-1.5 text-sm"
                    onClick={() =>
                      void (async () => {
                        if (!api || !selected) return;
                        try {
                          const inst = await api.start(selected.id, {});
                          setMessage(`Запущен инстанс #${inst.id}`);
                          setTab("instances");
                          await load();
                        } catch (err) {
                          setError(parseApiError(err));
                        }
                      })()
                    }
                  >
                    Запустить
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {tab === "instances" && (
        <div className="space-y-4">
          <ul className="space-y-2 rounded-xl border border-border bg-surface p-4 text-sm">
            {instances.map((i) => (
              <li key={i.id}>
                <button
                  type="button"
                  className="w-full rounded-lg border border-border px-3 py-2 text-left hover:bg-cream"
                  onClick={() =>
                    void (async () => {
                      if (!api) return;
                      try {
                        const detail = await api.getInstance(i.id);
                        setInstanceDetail({
                          instance: detail.instance,
                          children: detail.children || [],
                          bpmn_xml: detail.bpmn_xml,
                          active_element_ids: detail.active_element_ids || [],
                          work_tree: detail.work_tree || [],
                        });
                        setHighlightIds([]);
                      } catch (err) {
                        setError(parseApiError(err));
                      }
                    })()
                  }
                >
                  #{i.id} · {i.definition_name} · <strong>{i.status}</strong>
                  {i.error_message && (
                    <span className="ml-2 text-primary">{i.error_message}</span>
                  )}
                </button>
              </li>
            ))}
            {instances.length === 0 && (
              <li className="text-text-muted">Нет инстансов</li>
            )}
          </ul>
          {instanceDetail && (
            <div className="rounded-xl border border-border bg-surface p-4">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-semibold text-text">
                  Инстанс #{instanceDetail.instance.id} ·{" "}
                  {instanceDetail.instance.status}
                </h3>
                <div className="flex flex-wrap gap-3 text-xs">
                  {instanceDetail.instance.deal != null && (
                    <a
                      className="text-primary hover:underline"
                      href={`/deals?deal=${instanceDetail.instance.deal}`}
                    >
                      Сделка #{instanceDetail.instance.deal}
                    </a>
                  )}
                  {instanceDetail.instance.project != null && (
                    <a
                      className="text-primary hover:underline"
                      href={`/projects/${instanceDetail.instance.project}`}
                    >
                      Проект #{instanceDetail.instance.project}
                    </a>
                  )}
                </div>
              </div>
              <p className="mb-2 text-xs text-text-muted">
                Активные токены:{" "}
                {instanceDetail.active_element_ids.length
                  ? instanceDetail.active_element_ids.join(", ")
                  : "—"}
                {instanceDetail.instance.parent != null && (
                  <>
                    {" "}
                    · parent #
                    <button
                      type="button"
                      className="text-primary hover:underline"
                      onClick={() =>
                        void (async () => {
                          if (!api || instanceDetail.instance.parent == null) return;
                          try {
                            const detail = await api.getInstance(
                              instanceDetail.instance.parent,
                            );
                            setInstanceDetail({
                              instance: detail.instance,
                              children: detail.children || [],
                              bpmn_xml: detail.bpmn_xml,
                              active_element_ids: detail.active_element_ids || [],
                              work_tree: detail.work_tree || [],
                            });
                            setHighlightIds([]);
                          } catch (err) {
                            setError(parseApiError(err));
                          }
                        })()
                      }
                    >
                      {instanceDetail.instance.parent}
                    </button>
                    {instanceDetail.instance.subprocess_bpmn_id
                      ? ` · ${instanceDetail.instance.subprocess_bpmn_id}`
                      : ""}
                  </>
                )}
              </p>
              {instanceDetail.children.length > 0 && (
                <div className="mb-3 rounded-lg border border-border bg-cream px-3 py-2 text-xs">
                  <p className="mb-1 font-medium text-text">Дочерние SubProcess</p>
                  <ul className="space-y-1">
                    {instanceDetail.children.map((child) => (
                      <li key={child.id}>
                        <button
                          type="button"
                          className="text-primary hover:underline"
                          onClick={() =>
                            void (async () => {
                              if (!api) return;
                              try {
                                const detail = await api.getInstance(child.id);
                                setInstanceDetail({
                                  instance: detail.instance,
                                  children: detail.children || [],
                                  bpmn_xml: detail.bpmn_xml,
                                  active_element_ids:
                                    detail.active_element_ids || [],
                                  work_tree: detail.work_tree || [],
                                });
                                setHighlightIds([]);
                              } catch (err) {
                                setError(parseApiError(err));
                              }
                            })()
                          }
                        >
                          #{child.id} · {child.subprocess_bpmn_id || child.definition_name}{" "}
                          · {child.status}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <BpmnViewer
                xml={instanceDetail.bpmn_xml}
                activeElementIds={instanceDetail.active_element_ids}
                highlightElementIds={
                  highlightIds.length
                    ? highlightIds
                    : instanceDetail.instance.subprocess_bpmn_id
                      ? [instanceDetail.instance.subprocess_bpmn_id]
                      : []
                }
                height={320}
              />
              <div className="mt-3 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium text-text">
                    <GlossaryText text="Process-as-WBS" /> дерево
                  </p>
                  <button
                    type="button"
                    className="rounded-lg bg-secondary px-3 py-1 text-xs font-semibold text-white"
                    onClick={() =>
                      void (async () => {
                        if (!api || !instanceDetail) return;
                        try {
                          const result = await api.materializeWbs(
                            instanceDetail.instance.id,
                            { replace: instanceDetail.work_tree.length > 0 },
                          );
                          setInstanceDetail({
                            ...instanceDetail,
                            work_tree: result.tree || [],
                          });
                          setMessage(
                            result.created
                              ? `Materialized ${result.created} узлов`
                              : "Дерево синхронизировано",
                          );
                        } catch (err) {
                          setError(parseApiError(err));
                        }
                      })()
                    }
                  >
                    Materialize WBS
                  </button>
                </div>
                <ProcessWorkTree
                  tree={instanceDetail.work_tree}
                  onSelectBpmn={(id) => setHighlightIds([id])}
                  onPatch={
                    api
                      ? async (nodeId, body) => {
                          const result = await api.patchWorkNode(nodeId, body);
                          setInstanceDetail((cur) =>
                            cur
                              ? { ...cur, work_tree: result.tree }
                              : cur,
                          );
                          return result.tree;
                        }
                      : undefined
                  }
                />
              </div>
              <p className="mt-2 text-xs text-text-muted">
                <GlossaryText text="Inclusive Gateway" />: каждое истинное исходящее +
                optional default; join ждёт взятые ветки. Пример-пак:{" "}
                <code>or_inclusive</code>. Кнопки над схемой сворачивают содержимое{" "}
                <GlossaryText text="SubProcess" />.
              </p>
            </div>
          )}
        </div>
      )}

      {tab === "packs" && (
        <div className="space-y-3 rounded-xl border border-border bg-surface p-4">
          <p className="text-sm text-text-muted">
            Шаблоны ISO 9001/PDCA, ITIL Change, NIST Incident — не сертификация продукта.
          </p>
          <ul className="space-y-2">
            {packs.map((p) => (
              <li
                key={p.id}
                className="flex items-start justify-between gap-3 rounded-lg border border-border px-3 py-2"
              >
                <div>
                  <p className="font-medium text-text">{p.name}</p>
                  <p className="text-xs text-text-muted whitespace-pre-wrap">
                    {p.readme.slice(0, 200)}
                  </p>
                </div>
                <button
                  type="button"
                  className="shrink-0 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white"
                  onClick={() =>
                    void (async () => {
                      if (!api) return;
                      try {
                        await api.importPack(p.id);
                        setMessage(`Импортирован ${p.id}`);
                        await load();
                      } catch (err) {
                        setError(parseApiError(err));
                      }
                    })()
                  }
                >
                  Импорт
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {tab === "cases" && (
        <div className="space-y-4 rounded-xl border border-border bg-surface p-4">
          <button
            type="button"
            className="rounded-lg bg-secondary px-3 py-1.5 text-sm font-semibold text-white"
            onClick={() =>
              void (async () => {
                if (!api) return;
                try {
                  let def = caseDefs[0];
                  if (!def) {
                    def = await api.createCaseDefinition({
                      key: "support-case",
                      name: "Support case",
                      description: "CMMN-lite with depends_on",
                      plan_items: [
                        { id: "triage", name: "Triage", required: true },
                        {
                          id: "investigate",
                          name: "Investigate",
                          discretionary: true,
                          required: false,
                          depends_on: ["triage"],
                        },
                        {
                          id: "resolve",
                          name: "Resolve",
                          required: true,
                          depends_on: ["triage"],
                        },
                      ],
                      cmmn_xml: "",
                    });
                  }
                  await api.startCase({ definition_id: def.id, title: "Новый кейс" });
                  setMessage("Кейс создан");
                  await load();
                } catch (err) {
                  setError(parseApiError(err));
                }
              })()
            }
          >
            Создать support-кейс
          </button>
          <ul className="space-y-3 text-sm">
            {cases.map((c) => {
              const availableIds = new Set(
                (c.available_items || []).map((i) => i.id),
              );
              const plan =
                caseDefs.find((d) => d.id === c.definition)?.plan_items || [];
              return (
                <li key={c.id} className="rounded-lg border border-border p-3">
                  <p className="font-medium">
                    {c.title} · {c.status}
                  </p>
                  <p className="text-xs text-text-muted">{c.definition_name}</p>
                  {(c.required_incomplete || []).length > 0 && (
                    <p className="mt-1 text-xs text-primary">
                      Обязательные: {c.required_incomplete.join(", ")}
                    </p>
                  )}
                  <div className="mt-2 flex flex-wrap gap-2">
                    {plan.map((item) => {
                      const done = c.completed_items.includes(item.id);
                      const enabled =
                        !done &&
                        c.status === "open" &&
                        availableIds.has(item.id);
                      return (
                        <button
                          key={item.id}
                          type="button"
                          disabled={!enabled}
                          title={
                            item.depends_on?.length
                              ? `depends_on: ${item.depends_on.join(", ")}`
                              : undefined
                          }
                          className="rounded border border-border px-2 py-1 text-xs disabled:opacity-50"
                          onClick={() =>
                            void (async () => {
                              if (!api) return;
                              try {
                                await api.completeCaseItem(c.id, item.id);
                                await load();
                              } catch (err) {
                                setError(parseApiError(err));
                              }
                            })()
                          }
                        >
                          {done ? "✓ " : ""}
                          {item.name}
                          {item.discretionary ? " (opt)" : ""}
                        </button>
                      );
                    })}
                    {c.status === "open" && (
                      <button
                        type="button"
                        className="rounded border border-border px-2 py-1 text-xs"
                        onClick={() =>
                          void (async () => {
                            if (!api) return;
                            try {
                              await api.closeCase(c.id, false);
                              await load();
                            } catch (err) {
                              setError(parseApiError(err));
                            }
                          })()
                        }
                      >
                        Закрыть
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {tab === "dmn" && (
        <div className="space-y-4 rounded-xl border border-border bg-surface p-4 text-sm">
          <p className="text-text-muted">
            Decision tables (OMG XML + FEEL-lite). Импортируйте pack с `.dmn` или
            создайте определение через API.
          </p>
          <ul className="space-y-2">
            {decisions.map((d) => (
              <li
                key={d.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border px-3 py-2"
              >
                <span>
                  <strong>{d.name}</strong>{" "}
                  <span className="text-text-muted">({d.key})</span>
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    className="w-24 rounded border border-border bg-cream px-2 py-1 text-xs"
                    value={dmnScore}
                    onChange={(e) => setDmnScore(e.target.value)}
                    placeholder="score"
                  />
                  <button
                    type="button"
                    className="rounded-lg bg-primary px-3 py-1 text-xs font-semibold text-white"
                    onClick={() =>
                      void (async () => {
                        if (!api) return;
                        try {
                          const res = await api.evaluateDecision(d.id, {
                            score: Number(dmnScore),
                          });
                          setDmnResult(JSON.stringify(res.result, null, 2));
                        } catch (err) {
                          setError(parseApiError(err));
                        }
                      })()
                    }
                  >
                    Evaluate
                  </button>
                </div>
              </li>
            ))}
            {decisions.length === 0 && (
              <li className="text-text-muted">
                Нет DMN — импортируйте пакет iso9001_pdca
              </li>
            )}
          </ul>
          {dmnResult && (
            <pre className="overflow-x-auto rounded bg-cream p-3 text-xs">
              {dmnResult}
            </pre>
          )}
        </div>
      )}

      {tab === "ops" && ops && (
        <div className="space-y-4">
          <div className="grid gap-3 rounded-xl border border-border bg-surface p-4 text-sm sm:grid-cols-4">
            <div>
              Stuck: <strong>{ops.counts.stuck_instances}</strong>
              <span className="ml-1 text-xs text-text-muted">
                (&gt;{ops.thresholds.stuck_hours}ч / error)
              </span>
            </div>
            <div>
              Aging tasks: <strong>{ops.counts.aging_tasks}</strong>
              <span className="ml-1 text-xs text-text-muted">
                (&gt;{ops.thresholds.aging_hours}ч)
              </span>
            </div>
            <div>
              SLA breaches: <strong>{ops.counts.sla_breaches}</strong>
            </div>
            <div>
              Open tasks: <strong>{ops.counts.open_user_tasks}</strong>
              <Link
                to="/process-tasks"
                className="ml-2 text-xs text-primary"
              >
                Inbox →
              </Link>
            </div>
          </div>

          <section className="rounded-xl border border-border bg-surface p-4 text-sm">
            <h3 className="font-semibold text-text">Зависшие инстансы</h3>
            <ul className="mt-2 max-h-56 space-y-1 overflow-y-auto text-xs">
              {ops.stuck_instances.map((row) => (
                <li
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded border border-border px-2 py-1.5"
                >
                  <span>
                    #{row.id} · {row.definition_name || "—"} · {row.status}
                    {row.age_hours != null ? ` · ${row.age_hours}ч` : ""}
                    {row.reasons?.length ? ` · ${row.reasons.join(",")}` : ""}
                  </span>
                  <span className="flex gap-2">
                    {row.deal ? (
                      <Link to={`/deals?deal=${row.deal}`} className="text-primary">
                        Deal
                      </Link>
                    ) : null}
                    {row.project ? (
                      <Link to={`/projects/${row.project}`} className="text-primary">
                        Project
                      </Link>
                    ) : null}
                  </span>
                </li>
              ))}
              {ops.stuck_instances.length === 0 && (
                <li className="text-text-muted">Нет зависших инстансов</li>
              )}
            </ul>
          </section>

          <section className="rounded-xl border border-border bg-surface p-4 text-sm">
            <h3 className="font-semibold text-text">Старые open tasks</h3>
            <ul className="mt-2 max-h-56 space-y-1 overflow-y-auto text-xs">
              {ops.aging_tasks.map((row) => (
                <li
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded border border-border px-2 py-1.5"
                >
                  <span>
                    {row.name} · instance #{row.instance_id} · {row.age_hours}ч
                  </span>
                  <Link to="/process-tasks" className="text-primary">
                    Inbox
                  </Link>
                </li>
              ))}
              {ops.aging_tasks.length === 0 && (
                <li className="text-text-muted">Нет aging tasks</li>
              )}
            </ul>
          </section>

          <section className="rounded-xl border border-border bg-surface p-4 text-sm">
            <h3 className="font-semibold text-text">SLA / просроченные</h3>
            <ul className="mt-2 max-h-56 space-y-1 overflow-y-auto text-xs">
              {ops.sla_breaches.map((row) => (
                <li
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded border border-border px-2 py-1.5"
                >
                  <span>
                    {row.name} · overdue {row.overdue_hours}ч
                    {row.due_at ? ` · due ${row.due_at.slice(0, 16)}` : ""}
                  </span>
                  <Link to="/process-tasks" className="text-primary">
                    Inbox
                  </Link>
                </li>
              ))}
              {ops.sla_breaches.length === 0 && (
                <li className="text-text-muted">Нет просроченных задач</li>
              )}
            </ul>
          </section>
        </div>
      )}

      {tab === "adapters" && adapterCatalog && (
        <div className="space-y-4">
          <p className="text-sm text-text-muted">{adapterCatalog.dispatch_hint}</p>
          <section className="rounded-xl border border-border bg-surface p-4 text-sm">
            <h3 className="font-semibold text-text">ServiceTask adapters</h3>
            <ul className="mt-2 space-y-2">
              {adapterCatalog.adapters.map((item) => (
                <li
                  key={item.operation}
                  className="rounded border border-border px-3 py-2"
                >
                  <div className="font-medium text-text">
                    <code className="text-primary">{item.operation}</code> —{" "}
                    {item.label}
                  </div>
                  <p className="mt-0.5 text-xs text-text-muted">
                    {item.description}
                  </p>
                  {item.params.length > 0 && (
                    <p className="mt-1 text-xs text-text-muted">
                      params:{" "}
                      {item.params
                        .map(
                          (p) =>
                            `${p.name}${p.required ? "*" : ""}:${p.type}`,
                        )
                        .join(", ")}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </section>
          <section className="rounded-xl border border-border bg-surface p-4 text-sm">
            <h3 className="font-semibold text-text">Executable BPMN elements</h3>
            <ul className="mt-2 space-y-1 text-xs">
              {adapterCatalog.executable_elements.map((el) => (
                <li key={el.type}>
                  <code>{el.type}</code> · {el.status}
                  {el.note ? ` — ${el.note}` : ""}
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}

      {tab === "metrics" && metrics && (
        <div className="space-y-4">
          <div className="grid gap-3 rounded-xl border border-border bg-surface p-4 text-sm sm:grid-cols-3">
            <div>Всего инстансов: {metrics.instance_count}</div>
            <div>Активных: {metrics.active_count}</div>
            <div>Завершённых: {metrics.completed_count}</div>
            <div>Ошибок: {metrics.error_count}</div>
            <div>Open tasks: {metrics.open_user_tasks}</div>
            <div>Просрочено: {metrics.overdue_user_tasks}</div>
            <div>
              Avg cycle (ч):{" "}
              {metrics.avg_cycle_hours != null
                ? metrics.avg_cycle_hours.toFixed(2)
                : "—"}
            </div>
          </div>
          {mining && (
            <div className="space-y-3 rounded-xl border border-border bg-surface p-4 text-sm">
              <h3 className="font-semibold text-text">Process mining (lite)</h3>
              <p className="text-xs text-text-muted">
                Sample {mining.instance_sample} · events {mining.event_count} —
                DFG из ActivityInstance (не Celonis)
              </p>
              <div>
                <p className="mb-1 text-xs font-medium">Top DFG edges</p>
                <ul className="max-h-40 space-y-1 overflow-y-auto text-xs">
                  {mining.dfg.slice(0, 15).map((e) => (
                    <li key={`${e.from}->${e.to}`}>
                      {e.from} → {e.to} · {e.count}
                    </li>
                  ))}
                  {mining.dfg.length === 0 && (
                    <li className="text-text-muted">Нет рёбер — запустите процессы</li>
                  )}
                </ul>
              </div>
              <div>
                <p className="mb-1 text-xs font-medium">Bottlenecks (avg hours)</p>
                <ul className="max-h-32 space-y-1 overflow-y-auto text-xs">
                  {mining.bottlenecks.slice(0, 10).map((b) => (
                    <li key={b.node}>
                      {b.node}: {b.avg_hours.toFixed(3)} ч (n={b.samples})
                    </li>
                  ))}
                  {mining.bottlenecks.length === 0 && (
                    <li className="text-text-muted">—</li>
                  )}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
