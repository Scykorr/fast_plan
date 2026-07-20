import { useEffect, useState } from "react";

import { parseApiError } from "../../api/errors";
import type {
  AiDraftWbsDependency,
  AiDraftWbsNode,
  AiDraftTarget,
  ProjectCharter,
} from "../../api/projects";
import { useProjectsApi } from "../../hooks/useProjectsApi";

type DraftRisk = {
  title: string;
  description?: string;
  probability: number;
  impact: number;
  mitigation?: string;
  status?: string;
};

type Props = {
  projectId: number;
  target: AiDraftTarget;
  initialPrompt?: string;
  onPromptChange?: (target: AiDraftTarget, prompt: string) => void;
  onRisksApplied?: () => void | Promise<void>;
  onCharterApplied?: (charter: ProjectCharter) => void | Promise<void>;
  onWbsApplied?: () => void | Promise<void>;
};

const TARGET_LABELS: Record<AiDraftTarget, string> = {
  risks: "AI-черновик рисков",
  charter: "AI-черновик устава",
  wbs: "AI-черновик WBS/графика",
};

export function ProjectAIDraftButton({
  projectId,
  target,
  initialPrompt = "",
  onPromptChange,
  onRisksApplied,
  onCharterApplied,
  onWbsApplied,
}: Props) {
  const projectsApi = useProjectsApi();
  const [open, setOpen] = useState(false);
  const [prompt, setPrompt] = useState(initialPrompt);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState("");
  const [source, setSource] = useState("");
  const [draftRisks, setDraftRisks] = useState<DraftRisk[]>([]);
  const [draftCharter, setDraftCharter] = useState<ProjectCharter | null>(null);
  const [draftNodes, setDraftNodes] = useState<AiDraftWbsNode[]>([]);
  const [draftDependencies, setDraftDependencies] = useState<AiDraftWbsDependency[]>([]);
  const [refinement, setRefinement] = useState("");
  const [refineCount, setRefineCount] = useState(0);

  useEffect(() => {
    setPrompt(initialPrompt);
  }, [initialPrompt]);

  const label = TARGET_LABELS[target];

  const applyDraftResult = (
    draft: Awaited<ReturnType<NonNullable<typeof projectsApi>["draftProjectContent"]>>,
  ) => {
    setSource(draft.source);
    if ("saved_prompt" in draft && draft.saved_prompt) {
      onPromptChange?.(target, draft.saved_prompt);
    } else if (prompt.trim()) {
      onPromptChange?.(target, prompt.trim());
    }
    if (draft.target === "risks") {
      setDraftRisks(draft.risks);
      setDraftCharter(null);
      setDraftNodes([]);
      setDraftDependencies([]);
    } else if (draft.target === "charter") {
      setDraftCharter(draft.charter);
      setDraftRisks([]);
      setDraftNodes([]);
      setDraftDependencies([]);
    } else {
      setDraftNodes(draft.nodes);
      setDraftDependencies(draft.dependencies ?? []);
      setDraftRisks([]);
      setDraftCharter(null);
    }
  };

  const handleGenerate = async () => {
    if (!projectsApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const draft = await projectsApi.draftProjectContent(projectId, {
        target,
        prompt: prompt.trim() || undefined,
      });
      applyDraftResult(draft);
      setRefinement("");
      setRefineCount(0);
    } catch (err) {
      setError(parseApiError(err, "Не удалось сгенерировать черновик"));
    } finally {
      setLoading(false);
    }
  };

  const handleRefine = async () => {
    if (!projectsApi || target !== "wbs" || draftNodes.length === 0) {
      return;
    }
    if (!refinement.trim()) {
      setError("Опишите, что изменить в черновике");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const draft = await projectsApi.draftProjectContent(projectId, {
        target: "wbs",
        prompt: prompt.trim() || undefined,
        refinement: refinement.trim(),
        current_draft: {
          nodes: draftNodes,
          dependencies: draftDependencies,
        },
      });
      if (draft.target !== "wbs") {
        throw new Error("Unexpected draft target");
      }
      applyDraftResult(draft);
      setRefinement("");
      setRefineCount((count) => count + 1);
    } catch (err) {
      setError(parseApiError(err, "Не удалось уточнить черновик"));
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    if (!projectsApi) {
      return;
    }
    setApplying(true);
    setError("");
    try {
      if (target === "risks") {
        for (const risk of draftRisks) {
          await projectsApi.createRisk(projectId, {
            title: risk.title,
            description: risk.description ?? "",
            probability: risk.probability,
            impact: risk.impact,
            mitigation: risk.mitigation ?? "",
            status: risk.status ?? "open",
          });
        }
        await onRisksApplied?.();
      } else if (target === "charter" && draftCharter) {
        const updated = await projectsApi.patchCharter(projectId, draftCharter);
        await onCharterApplied?.(updated);
      } else if (target === "wbs") {
        await projectsApi.applyAiDraft(projectId, {
          target: "wbs",
          nodes: draftNodes,
          dependencies: draftDependencies,
        });
        await onWbsApplied?.();
      }
      setOpen(false);
      setPrompt(initialPrompt);
      setDraftRisks([]);
      setDraftCharter(null);
      setDraftNodes([]);
      setDraftDependencies([]);
      setRefinement("");
      setRefineCount(0);
    } catch (err) {
      setError(parseApiError(err, "Не удалось применить черновик"));
    } finally {
      setApplying(false);
    }
  };

  const hasDraft =
    target === "risks"
      ? draftRisks.length > 0
      : target === "charter"
        ? draftCharter !== null
        : draftNodes.length > 0;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-lg border border-border bg-cream px-3 py-1.5 text-sm font-medium text-text hover:bg-border/30"
      >
        {label}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-border bg-surface p-5 shadow-lg">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-text">{label}</h3>
                <p className="mt-1 text-sm text-text-muted">
                  OpenAI или Ollama (локально, бесплатно) при наличии настроек,
                  иначе эвристический черновик. Промпт сохраняется для проекта.
                </p>
              </div>
              <button
                type="button"
                className="text-sm text-text-muted hover:text-text"
                onClick={() => setOpen(false)}
              >
                Закрыть
              </button>
            </div>

            <label className="mb-3 block text-sm">
              <span className="mb-1 block font-medium text-text">
                Контекст / промпт (сохраняется per-project)
              </span>
              <textarea
                rows={3}
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                placeholder="Например: фокус на интеграции с внешним API"
              />
            </label>

            <button
              type="button"
              disabled={loading}
              onClick={() => void handleGenerate()}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
            >
              {loading ? "Генерация..." : "Сгенерировать"}
            </button>

            {error && <p className="mt-3 text-sm text-primary">{error}</p>}

            {hasDraft && (
              <div className="mt-4 space-y-3">
                {source && (
                  <p className="text-xs text-text-muted">
                    Источник:{" "}
                    {source === "openai"
                      ? "OpenAI"
                      : source === "ollama"
                        ? "Ollama"
                        : "эвристика"}
                  </p>
                )}

                {target === "risks" && (
                  <ul className="space-y-2 text-sm">
                    {draftRisks.map((risk, index) => (
                      <li
                        key={`${risk.title}-${index}`}
                        className="rounded-lg border border-border px-3 py-2"
                      >
                        <p className="font-medium text-text">{risk.title}</p>
                        {risk.description && (
                          <p className="mt-1 text-text-muted">{risk.description}</p>
                        )}
                        <p className="mt-1 text-xs text-text-muted">
                          P{risk.probability} × I{risk.impact}
                          {risk.mitigation ? ` · ${risk.mitigation}` : ""}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}

                {target === "charter" && draftCharter && (
                  <div className="grid gap-3 text-sm sm:grid-cols-2">
                    {(
                      [
                        ["goals", "Цели"],
                        ["success_criteria", "Критерии успеха"],
                        ["constraints", "Ограничения"],
                        ["assumptions", "Допущения"],
                      ] as const
                    ).map(([key, title]) => (
                      <div key={key} className="rounded-lg border border-border p-3">
                        <p className="font-medium text-text">{title}</p>
                        <p className="mt-1 whitespace-pre-wrap text-text-muted">
                          {draftCharter[key]}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                {target === "wbs" && (
                  <div className="space-y-3 text-sm">
                    {refineCount > 0 && (
                      <p className="text-xs text-text-muted">
                        Уточнений: {refineCount}
                      </p>
                    )}
                    <ul className="space-y-2">
                      {draftNodes.map((node) => (
                        <li
                          key={node.code}
                          className="rounded-lg border border-border px-3 py-2"
                        >
                          <p className="font-medium text-text">
                            {node.code} · {node.title}
                          </p>
                          <p className="mt-1 text-xs text-text-muted">
                            {node.node_type ?? "work_package"}
                            {node.parent_code ? ` · parent ${node.parent_code}` : ""}
                            {node.duration_days != null
                              ? ` · ${node.duration_days} дн.`
                              : ""}
                          </p>
                        </li>
                      ))}
                    </ul>
                    {draftDependencies.length > 0 && (
                      <p className="text-xs text-text-muted">
                        Зависимостей: {draftDependencies.length}
                      </p>
                    )}
                    <label className="block text-sm">
                      <span className="mb-1 block font-medium text-text">
                        Уточнение черновика
                      </span>
                      <textarea
                        rows={2}
                        value={refinement}
                        onChange={(event) => setRefinement(event.target.value)}
                        className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                        placeholder="Например: добавь этап тестирования и деплой"
                      />
                    </label>
                    <button
                      type="button"
                      disabled={loading || !refinement.trim()}
                      onClick={() => void handleRefine()}
                      className="rounded-lg border border-border bg-cream px-4 py-2 text-sm font-medium text-text hover:bg-border/30 disabled:opacity-60"
                    >
                      {loading ? "Уточнение..." : "Уточнить черновик"}
                    </button>
                  </div>
                )}

                <button
                  type="button"
                  disabled={applying}
                  onClick={() => void handleApply()}
                  className="rounded-lg bg-secondary px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-60"
                >
                  {applying ? "Применение..." : "Применить черновик"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
