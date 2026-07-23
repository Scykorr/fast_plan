import { useCallback, useEffect, useState, type FormEvent } from "react";

import { parseApiError } from "../api/errors";
import type {
  CaseDefinition,
  CaseInstance,
  DecisionDefinition,
  ProcessDefinition,
  ProcessInstance,
  ProcessMetrics,
  ProcessMining,
  ProcessPack,
} from "../api/process";
import { BpmnModelerEditor } from "../components/process/BpmnModelerEditor";
import { BpmnViewer } from "../components/process/BpmnViewer";
import { ErrorMessage } from "../components/ErrorMessage";
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
  const [instanceDetail, setInstanceDetail] = useState<{
    instance: ProcessInstance;
    bpmn_xml: string;
    active_element_ids: string[];
  } | null>(null);
  const [tab, setTab] = useState<
    "defs" | "instances" | "packs" | "cases" | "dmn" | "metrics"
  >("defs");

  const load = useCallback(async () => {
    if (!api) return;
    try {
      const [defs, inst, packList, m, mine, caseList, caseDefList, decisionList] =
        await Promise.all([
          api.listDefinitions(),
          api.listInstances(),
          api.listPacks(),
          api.metrics(),
          api.mining(),
          api.listCases(),
          api.listCaseDefinitions(),
          api.listDecisions(),
        ]);
      setDefinitions(defs);
      setInstances(inst);
      setPacks(packList);
      setMetrics(m);
      setMining(mine);
      setCases(caseList);
      setCaseDefs(caseDefList);
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
          P8: BPMN 2.0 + SpiffWorkflow · рядом с CRM-автоматизациями (P6e)
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
            {label}
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
                          await api.publish(selected.id);
                          setMessage("Опубликовано");
                          await load();
                        } catch (err) {
                          setError(parseApiError(err));
                        }
                      })()
                    }
                  >
                    Опубликовать
                  </button>
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
                          bpmn_xml: detail.bpmn_xml,
                          active_element_ids: detail.active_element_ids || [],
                        });
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
              </p>
              <BpmnViewer
                xml={instanceDetail.bpmn_xml}
                activeElementIds={instanceDetail.active_element_ids}
                height={320}
              />
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
