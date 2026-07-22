import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { parseApiError } from "../api/errors";
import type { CrmLead, CrmLeadStatus } from "../api/crm";
import type { WorkspaceMember } from "../api/workspace";
import { ErrorMessage } from "../components/ErrorMessage";
import { useCrmApi } from "../hooks/useCrmApi";
import { useWorkspace } from "../context/WorkspaceContext";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

const STATUS_LABELS: Record<CrmLeadStatus, string> = {
  new: "Новый",
  contacted: "Контакт",
  qualified: "Квалифицирован",
  disqualified: "Отклонён",
  converted: "В сделку",
};

const SOURCES = ["website", "form", "referral", "partner", "ads", "cold", "other"];

export function LeadsPage() {
  const crmApi = useCrmApi();
  const workspaceApi = useWorkspaceApi();
  const { workspaceEpoch } = useWorkspace();
  const navigate = useNavigate();
  const [leads, setLeads] = useState<CrmLead[]>([]);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<CrmLeadStatus | "">("");
  const [selected, setSelected] = useState<CrmLead | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    company_name: "",
    source: "website",
  });

  const load = useCallback(async () => {
    if (!crmApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await crmApi.listLeads({
        q: query,
        status: statusFilter || undefined,
      });
      setLeads(data);
      if (selected) {
        setSelected(data.find((lead) => lead.id === selected.id) ?? null);
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить лиды"));
    } finally {
      setLoading(false);
    }
  }, [crmApi, query, statusFilter, selected?.id]);

  useEffect(() => {
    void load();
  }, [crmApi, query, statusFilter, workspaceEpoch]);

  useEffect(() => {
    if (!workspaceApi) {
      return;
    }
    void workspaceApi.getMembers().then(setMembers).catch(() => undefined);
  }, [workspaceApi, workspaceEpoch]);

  const createLead = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi || !form.full_name.trim()) {
      return;
    }
    try {
      const created = await crmApi.createLead({
        ...form,
        full_name: form.full_name.trim(),
        assign: "round_robin",
      });
      setForm({
        full_name: "",
        email: "",
        phone: "",
        company_name: "",
        source: "website",
      });
      setSelected(created);
      setMessage(`Лид создан, score ${created.score}`);
      await load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const dupes = (err.data as { duplicates?: CrmLead[] })?.duplicates ?? [];
        setError(
          `Возможный дубликат: ${dupes.map((d) => d.full_name).join(", ") || "совпадение email/phone"}`,
        );
        return;
      }
      setError(parseApiError(err, "Не удалось создать лид"));
    }
  };

  const assignRoundRobin = async () => {
    if (!crmApi || !selected) {
      return;
    }
    try {
      const updated = await crmApi.assignLead(selected.id, {
        mode: "round_robin",
      });
      setSelected(updated);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось назначить"));
    }
  };

  const assignManual = async (userId: number | null) => {
    if (!crmApi || !selected) {
      return;
    }
    try {
      if (userId == null) {
        const updated = await crmApi.patchLead(selected.id, {
          assigned_to_id: null,
        });
        setSelected(updated);
      } else {
        const updated = await crmApi.assignLead(selected.id, {
          mode: "manual",
          user_id: userId,
        });
        setSelected(updated);
      }
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось назначить"));
    }
  };

  const convert = async () => {
    if (!crmApi || !selected) {
      return;
    }
    try {
      const result = await crmApi.convertLead(selected.id);
      navigate(`/deals?deal=${result.deal.id}`);
    } catch (err) {
      setError(parseApiError(err, "Не удалось конвертировать"));
    }
  };

  const importCsv = async (file: File | null) => {
    if (!crmApi || !file) {
      return;
    }
    try {
      const result = await crmApi.importLeads(file, "round_robin");
      setMessage(
        `Импорт: создано ${result.created}, пропущено ${result.skipped} (дубликаты ${result.duplicates})`,
      );
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось импортировать CSV"));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text">Лиды</h1>
          <p className="mt-1 text-sm text-text-muted">
            Import · score · assignment · convert → Deal (P6d)
          </p>
        </div>
        <label className="cursor-pointer rounded-lg border border-border bg-cream px-3 py-1.5 text-sm">
          CSV import
          <input
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(event) => {
              void importCsv(event.target.files?.[0] ?? null);
              event.target.value = "";
            }}
          />
        </label>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      {message && <p className="text-sm text-secondary">{message}</p>}

      <div className="flex flex-wrap gap-2">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Поиск…"
          className="min-w-[12rem] flex-1 rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
        />
        <select
          value={statusFilter}
          onChange={(event) =>
            setStatusFilter((event.target.value || "") as CrmLeadStatus | "")
          }
          className="rounded-lg border border-border bg-cream px-2 py-1.5 text-sm"
        >
          <option value="">Все статусы</option>
          {(Object.keys(STATUS_LABELS) as CrmLeadStatus[]).map((status) => (
            <option key={status} value={status}>
              {STATUS_LABELS[status]}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <div className="space-y-4">
          <form
            onSubmit={(event) => void createLead(event)}
            className="space-y-2 rounded-xl border border-border bg-surface p-4"
          >
            <h2 className="text-sm font-semibold text-text">Новый лид</h2>
            <input
              value={form.full_name}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, full_name: event.target.value }))
              }
              placeholder="Имя *"
              className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              required
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                value={form.email}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, email: event.target.value }))
                }
                placeholder="Email"
                className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              />
              <input
                value={form.phone}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, phone: event.target.value }))
                }
                placeholder="Телефон"
                className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input
                value={form.company_name}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    company_name: event.target.value,
                  }))
                }
                placeholder="Компания"
                className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              />
              <select
                value={form.source}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, source: event.target.value }))
                }
                className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
              >
                {SOURCES.map((source) => (
                  <option key={source} value={source}>
                    {source}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
            >
              Создать (+ round-robin)
            </button>
          </form>

          <div className="rounded-xl border border-border bg-surface">
            {loading ? (
              <p className="p-4 text-sm text-text-muted">Загрузка…</p>
            ) : leads.length === 0 ? (
              <p className="p-4 text-sm text-text-muted">Пока нет лидов</p>
            ) : (
              <ul className="divide-y divide-border">
                {leads.map((lead) => (
                  <li key={lead.id}>
                    <button
                      type="button"
                      onClick={() => setSelected(lead)}
                      className={`w-full px-4 py-3 text-left hover:bg-cream ${
                        selected?.id === lead.id ? "bg-cream" : ""
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="font-medium text-text">{lead.full_name}</p>
                        <span className="text-xs font-semibold text-primary">
                          {lead.score}
                        </span>
                      </div>
                      <p className="text-xs text-text-muted">
                        {[
                          STATUS_LABELS[lead.status],
                          lead.company_name,
                          lead.source,
                          lead.assigned_to_email,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                      {(lead.duplicate_ids?.length ?? 0) > 0 && (
                        <p className="mt-1 text-[10px] text-amber-700 dark:text-amber-300">
                          Дубликаты: {lead.duplicate_ids?.join(", ")}
                        </p>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-surface p-4">
          {!selected ? (
            <p className="text-sm text-text-muted">Выберите лид</p>
          ) : (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold text-text">{selected.full_name}</h2>
              <p className="text-sm text-text-muted">
                Score {selected.score} · {STATUS_LABELS[selected.status]}
              </p>
              <div className="space-y-1 text-sm text-text-muted">
                {selected.email && <p>Email: {selected.email}</p>}
                {selected.phone && <p>Телефон: {selected.phone}</p>}
                {selected.company_name && <p>Компания: {selected.company_name}</p>}
                {selected.source && <p>Источник: {selected.source}</p>}
              </div>

              <div>
                <label className="text-xs text-text-muted">Ответственный</label>
                <div className="mt-1 flex flex-wrap gap-2">
                  <select
                    value={selected.assigned_to ?? ""}
                    onChange={(event) => {
                      void assignManual(
                        event.target.value ? Number(event.target.value) : null,
                      );
                    }}
                    className="rounded-lg border border-border bg-cream px-2 py-1.5 text-sm"
                  >
                    <option value="">Не назначен</option>
                    {members.map((member) => (
                      <option key={member.id} value={member.user_id}>
                        {member.email}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => void assignRoundRobin()}
                    className="rounded-lg border border-border px-3 py-1.5 text-sm"
                  >
                    Round-robin
                  </button>
                </div>
              </div>

              {selected.status !== "converted" ? (
                <button
                  type="button"
                  onClick={() => void convert()}
                  className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
                >
                  Конвертировать в сделку
                </button>
              ) : (
                <p className="text-sm text-secondary">
                  Сделка:{" "}
                  {selected.deal ? (
                    <Link to="/deals" className="text-primary hover:underline">
                      {selected.deal_title ?? `#${selected.deal}`}
                    </Link>
                  ) : (
                    "—"
                  )}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
