import { useState } from "react";

import { parseApiError } from "../../api/errors";
import type { ProjectCharter } from "../../api/projects";
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
  target: "risks" | "charter";
  onRisksApplied?: () => void | Promise<void>;
  onCharterApplied?: (charter: ProjectCharter) => void | Promise<void>;
};

export function ProjectAIDraftButton({
  projectId,
  target,
  onRisksApplied,
  onCharterApplied,
}: Props) {
  const projectsApi = useProjectsApi();
  const [open, setOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState("");
  const [source, setSource] = useState("");
  const [draftRisks, setDraftRisks] = useState<DraftRisk[]>([]);
  const [draftCharter, setDraftCharter] = useState<ProjectCharter | null>(null);

  const label = target === "risks" ? "AI-черновик рисков" : "AI-черновик устава";

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
      setSource(draft.source);
      if (draft.target === "risks") {
        setDraftRisks(draft.risks);
        setDraftCharter(null);
      } else {
        setDraftCharter(draft.charter);
        setDraftRisks([]);
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось сгенерировать черновик"));
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
      } else if (draftCharter) {
        const updated = await projectsApi.patchCharter(projectId, draftCharter);
        await onCharterApplied?.(updated);
      }
      setOpen(false);
      setPrompt("");
      setDraftRisks([]);
      setDraftCharter(null);
    } catch (err) {
      setError(parseApiError(err, "Не удалось применить черновик"));
    } finally {
      setApplying(false);
    }
  };

  const hasDraft =
    target === "risks" ? draftRisks.length > 0 : draftCharter !== null;

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
                  OpenAI при наличии ключа, иначе эвристический черновик.
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
                Дополнительный контекст (необязательно)
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

            {error && (
              <p className="mt-3 text-sm text-primary">{error}</p>
            )}

            {hasDraft && (
              <div className="mt-4 space-y-3">
                {source && (
                  <p className="text-xs text-text-muted">
                    Источник: {source === "openai" ? "OpenAI" : "эвристика"}
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
