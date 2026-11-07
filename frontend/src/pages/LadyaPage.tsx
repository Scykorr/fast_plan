import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router-dom";

import { parseApiError } from "../api/errors";
import type {
  IntakeRequest,
  Laboratory,
  LaboratoryKind,
  LadyaPackage,
  LadyaStatusEvent,
  PackageStatus,
} from "../api/ladya";
import type { DeliveryTask } from "../api/delivery";
import { ErrorMessage } from "../components/ErrorMessage";
import { useTheme } from "../context/ThemeContext";
import { useWorkspace } from "../context/WorkspaceContext";
import { useDeliveryApi } from "../hooks/useDeliveryApi";
import { useLadyaApi } from "../hooks/useLadyaApi";

const LAB_KINDS: Array<{ value: LaboratoryKind; label: string }> = [
  { value: "central_lad", label: "Центральный ЛАД" },
  { value: "lab0", label: "Lab-0" },
  { value: "private_lab", label: "Частная" },
  { value: "external_intake", label: "Вход / очередь" },
];

const STATUS_LABELS: Record<PackageStatus, string> = {
  draft: "Черновик",
  submitted: "Отправлен",
  accepted: "Принят",
  in_progress: "В работе",
  returned: "Возвращён",
  closed: "Закрыт",
  rejected: "Отклонён",
};

const NEXT_STATUSES: Partial<Record<PackageStatus, PackageStatus[]>> = {
  draft: ["submitted", "rejected"],
  submitted: ["accepted", "rejected", "returned"],
  accepted: ["in_progress", "returned", "rejected"],
  in_progress: ["returned", "closed"],
  returned: ["submitted", "accepted", "in_progress", "closed", "rejected"],
};

function SubNav() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    [
      "rounded-lg px-3 py-1.5 text-sm font-medium",
      isActive ? "bg-cream text-primary" : "text-text-muted hover:bg-cream",
    ].join(" ");

  return (
    <div className="flex flex-wrap gap-2 border-b border-border pb-3">
      <NavLink to="/ladya/labs" className={linkClass}>
        Лаборатории
      </NavLink>
      <NavLink to="/ladya/packages" end className={linkClass}>
        Пакеты
      </NavLink>
      <NavLink to="/ladya/intake" className={linkClass}>
        Вход (Intake)
      </NavLink>
    </div>
  );
}

function LabsPanel() {
  const api = useLadyaApi();
  const { workspaceEpoch } = useWorkspace();
  const [labs, setLabs] = useState<Laboratory[]>([]);
  const [error, setError] = useState("");
  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<LaboratoryKind>("private_lab");

  const load = useCallback(async () => {
    if (!api) return;
    try {
      setLabs(await api.listLaboratories());
      setError("");
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить лаборатории"));
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const onCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!api) return;
    try {
      await api.createLaboratory({ slug, title, kind });
      setSlug("");
      setTitle("");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать лабораторию"));
    }
  };

  return (
    <div className="space-y-4">
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      <form
        onSubmit={(e) => void onCreate(e)}
        className="grid gap-3 rounded-xl border border-border bg-surface p-4 md:grid-cols-4"
      >
        <input
          className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          placeholder="slug"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          required
        />
        <input
          className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          placeholder="Название"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <select
          className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          value={kind}
          onChange={(e) => setKind(e.target.value as LaboratoryKind)}
        >
          {LAB_KINDS.map((row) => (
            <option key={row.value} value={row.value}>
              {row.label}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white"
        >
          Создать
        </button>
      </form>
      <div className="overflow-x-auto rounded-xl border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-cream text-left text-text-muted">
              <th className="px-4 py-3">Название</th>
              <th className="px-4 py-3">Slug</th>
              <th className="px-4 py-3">Тип</th>
              <th className="px-4 py-3">Активна</th>
            </tr>
          </thead>
          <tbody>
            {labs.map((lab) => (
              <tr key={lab.id} className="border-b border-border/60">
                <td className="px-4 py-3">
                  <Link
                    className="text-primary hover:underline"
                    to={`/ladya/labs/${lab.id}`}
                  >
                    {lab.title}
                  </Link>
                </td>
                <td className="px-4 py-3 text-text-muted">{lab.slug}</td>
                <td className="px-4 py-3">
                  {LAB_KINDS.find((k) => k.value === lab.kind)?.label ?? lab.kind}
                </td>
                <td className="px-4 py-3">{lab.is_active ? "да" : "нет"}</td>
              </tr>
            ))}
            {labs.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-text-muted">
                  Лабораторий пока нет
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PackagesPanel() {
  const api = useLadyaApi();
  const navigate = useNavigate();
  const { workspaceEpoch } = useWorkspace();
  const [packages, setPackages] = useState<LadyaPackage[]>([]);
  const [labs, setLabs] = useState<Laboratory[]>([]);
  const [events, setEvents] = useState<LadyaStatusEvent[]>([]);
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [fromLab, setFromLab] = useState<number | "">("");
  const [toLab, setToLab] = useState<number | "">("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterFrom, setFilterFrom] = useState<number | "">("");
  const [filterTo, setFilterTo] = useState<number | "">("");
  const [filterQ, setFilterQ] = useState("");

  const load = useCallback(async () => {
    if (!api) return;
    try {
      const [pkgRows, labRows, eventRows] = await Promise.all([
        api.listPackages({
          status: filterStatus || undefined,
          from_lab: filterFrom === "" ? undefined : filterFrom,
          to_lab: filterTo === "" ? undefined : filterTo,
          q: filterQ.trim() || undefined,
        }),
        api.listLaboratories(),
        api.listEvents(12),
      ]);
      setPackages(pkgRows);
      setLabs(labRows);
      setEvents(eventRows);
      setError("");
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить пакеты"));
    }
  }, [api, filterFrom, filterQ, filterStatus, filterTo]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const labTitle = useMemo(() => {
    const map = new Map(labs.map((l) => [l.id, l.title]));
    return (id: number | null) => (id == null ? "—" : map.get(id) ?? `#${id}`);
  }, [labs]);

  const onCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!api) return;
    try {
      const created = await api.createPackage({
        title,
        summary,
        from_laboratory: fromLab === "" ? null : fromLab,
        to_laboratory: toLab === "" ? null : toLab,
      });
      setTitle("");
      setSummary("");
      navigate(`/ladya/packages/${created.id}`);
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать пакет"));
    }
  };

  return (
    <div className="space-y-4">
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      {events.length > 0 && (
        <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
          <h3 className="text-sm font-semibold">Лента событий контура</h3>
          {events.map((event) => (
            <button
              key={event.id}
              type="button"
              className="block w-full text-left text-sm text-text-muted hover:text-primary"
              onClick={() =>
                event.package_id &&
                navigate(`/ladya/packages/${event.package_id}`)
              }
            >
              {event.package_code}: {event.from_status || "—"} → {event.to_status}
              {event.reason ? ` — ${event.reason}` : ""}
            </button>
          ))}
        </div>
      )}
      <form
        onSubmit={(e) => void onCreate(e)}
        className="grid gap-3 rounded-xl border border-border bg-surface p-4 md:grid-cols-2"
      >
        <input
          className="rounded-lg border border-border bg-cream px-3 py-2 text-sm md:col-span-2"
          placeholder="Заголовок пакета"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <textarea
          className="rounded-lg border border-border bg-cream px-3 py-2 text-sm md:col-span-2"
          placeholder="Краткое описание"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={2}
        />
        <select
          className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          value={fromLab}
          onChange={(e) =>
            setFromLab(e.target.value === "" ? "" : Number(e.target.value))
          }
        >
          <option value="">От (лаборатория)</option>
          {labs.map((lab) => (
            <option key={lab.id} value={lab.id}>
              {lab.title}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          value={toLab}
          onChange={(e) =>
            setToLab(e.target.value === "" ? "" : Number(e.target.value))
          }
        >
          <option value="">Кому (лаборатория)</option>
          {labs.map((lab) => (
            <option key={lab.id} value={lab.id}>
              {lab.title}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white md:col-span-2"
        >
          Создать пакет
        </button>
      </form>

      <div className="grid gap-2 rounded-xl border border-border bg-surface p-3 md:grid-cols-4">
        <select
          className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
        >
          <option value="">Все статусы</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          value={filterFrom}
          onChange={(e) =>
            setFilterFrom(e.target.value === "" ? "" : Number(e.target.value))
          }
        >
          <option value="">От (фильтр)</option>
          {labs.map((lab) => (
            <option key={lab.id} value={lab.id}>
              {lab.title}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          value={filterTo}
          onChange={(e) =>
            setFilterTo(e.target.value === "" ? "" : Number(e.target.value))
          }
        >
          <option value="">Кому (фильтр)</option>
          {labs.map((lab) => (
            <option key={lab.id} value={lab.id}>
              {lab.title}
            </option>
          ))}
        </select>
        <input
          className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          placeholder="Поиск по названию"
          value={filterQ}
          onChange={(e) => setFilterQ(e.target.value)}
        />
      </div>

      <div className="overflow-x-auto rounded-xl border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-cream text-left text-text-muted">
              <th className="px-4 py-3">Код</th>
              <th className="px-4 py-3">Название</th>
              <th className="px-4 py-3">Статус</th>
              <th className="px-4 py-3">От → Кому</th>
            </tr>
          </thead>
          <tbody>
            {packages.map((pkg) => (
              <tr
                key={pkg.id}
                className="cursor-pointer border-b border-border/60 hover:bg-cream/60"
                onClick={() => navigate(`/ladya/packages/${pkg.id}`)}
              >
                <td className="px-4 py-3 font-medium">{pkg.display_code}</td>
                <td className="px-4 py-3">{pkg.title}</td>
                <td className="px-4 py-3">{STATUS_LABELS[pkg.status]}</td>
                <td className="px-4 py-3 text-text-muted">
                  {labTitle(pkg.from_laboratory)} → {labTitle(pkg.to_laboratory)}
                </td>
              </tr>
            ))}
            {packages.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-text-muted">
                  Пакетов пока нет
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PackageDetailPanel() {
  const { packageId } = useParams();
  const api = useLadyaApi();
  const deliveryApi = useDeliveryApi();
  const navigate = useNavigate();
  const [pkg, setPkg] = useState<LadyaPackage | null>(null);
  const [labs, setLabs] = useState<Laboratory[]>([]);
  const [deliveryTasks, setDeliveryTasks] = useState<DeliveryTask[]>([]);
  const [linkedTask, setLinkedTask] = useState<DeliveryTask | null>(null);
  const [taskPick, setTaskPick] = useState<number | "">("");
  const [opsAvailable, setOpsAvailable] = useState(false);
  const [packageMaxBytes, setPackageMaxBytes] = useState(256 * 1024 * 1024);
  const [transferLab, setTransferLab] = useState<number | "">("");
  const [transferReason, setTransferReason] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [reason, setReason] = useState("");

  const id = Number(packageId);

  const load = useCallback(async () => {
    if (!api || !Number.isFinite(id)) return;
    try {
      const [row, labRows] = await Promise.all([
        api.getPackage(id),
        api.listLaboratories(),
      ]);
      setPkg(row);
      setLabs(labRows);
      setError("");

      try {
        const ladyaSettings = await api.getSettings();
        setPackageMaxBytes(ladyaSettings.package_max_bytes || 256 * 1024 * 1024);
      } catch {
        /* keep default */
      }

      if (deliveryApi) {
        try {
          const settings = await deliveryApi.getSettings();
          setOpsAvailable(Boolean(settings.agent_ops_enabled));
          if (settings.agent_ops_enabled) {
            const tasks = await deliveryApi.listTasks();
            setDeliveryTasks(tasks);
            if (row.linked_delivery_task) {
              const found =
                tasks.find((t) => t.id === row.linked_delivery_task) ??
                (await deliveryApi.getTask(row.linked_delivery_task));
              setLinkedTask(found);
              setTaskPick(found.id);
            } else {
              setLinkedTask(null);
              setTaskPick("");
            }
          } else {
            setDeliveryTasks([]);
            setLinkedTask(null);
            setTaskPick("");
          }
        } catch {
          setOpsAvailable(false);
          setDeliveryTasks([]);
          setLinkedTask(null);
        }
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить пакет"));
    }
  }, [api, deliveryApi, id]);

  useEffect(() => {
    void load();
  }, [load]);

  const labTitle = (labId: number | null) => {
    if (labId == null) return "—";
    return labs.find((l) => l.id === labId)?.title ?? `#${labId}`;
  };

  const onTransition = async (status: PackageStatus) => {
    if (!api || !pkg) return;
    try {
      setPkg(await api.transitionPackage(pkg.id, { status, reason }));
      setReason("");
    } catch (err) {
      setError(parseApiError(err, "Не удалось сменить статус"));
    }
  };

  const onUpload = async (file: File | null) => {
    if (!api || !pkg || !file) return;
    if (file.size > packageMaxBytes) {
      setError(
        `Файл ${file.size} байт превышает лимит ${packageMaxBytes} (LADYA_PACKAGE_MAX_BYTES).`,
      );
      return;
    }
    setUploading(true);
    try {
      await api.uploadPackageFile(pkg.id, file);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить файл"));
    } finally {
      setUploading(false);
    }
  };

  const onCreateDeliveryTask = async () => {
    if (!api || !pkg) return;
    try {
      const result = await api.createDeliveryTask(pkg.id);
      setPkg(result.package);
      if (deliveryApi) {
        setLinkedTask(await deliveryApi.getTask(result.delivery_task.id));
        setTaskPick(result.delivery_task.id);
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать DeliveryTask"));
    }
  };

  const onTransfer = async () => {
    if (!api || !pkg || transferLab === "") return;
    try {
      setPkg(
        await api.transferPackage(pkg.id, {
          to_laboratory: transferLab,
          reason: transferReason,
        }),
      );
      setTransferReason("");
    } catch (err) {
      setError(parseApiError(err, "Не удалось передать пакет"));
    }
  };

  const onBuildManifest = async () => {
    if (!api || !pkg) return;
    try {
      const result = await api.buildManifest(pkg.id);
      setPkg({ ...pkg, manifest_sha256: result.manifest_sha256 });
      const blob = new Blob([JSON.stringify(result.manifest, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${pkg.display_code}-manifest.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(parseApiError(err, "Не удалось собрать манифест"));
    }
  };

  const onLinkTask = async () => {
    if (!api || !pkg || taskPick === "") return;
    try {
      const updated = await api.patchPackage(pkg.id, {
        linked_delivery_task: taskPick,
      });
      setPkg(updated);
      const task =
        deliveryTasks.find((t) => t.id === taskPick) ??
        (deliveryApi ? await deliveryApi.getTask(taskPick) : null);
      setLinkedTask(task);
    } catch (err) {
      setError(parseApiError(err, "Не удалось связать DeliveryTask"));
    }
  };

  const onUnlinkTask = async () => {
    if (!api || !pkg) return;
    try {
      const updated = await api.patchPackage(pkg.id, {
        linked_delivery_task: null,
      });
      setPkg(updated);
      setLinkedTask(null);
      setTaskPick("");
    } catch (err) {
      setError(parseApiError(err, "Не удалось отвязать DeliveryTask"));
    }
  };

  if (!Number.isFinite(id)) {
    return <Navigate to="/ladya/packages" replace />;
  }

  if (!pkg) {
    return (
      <div className="space-y-3">
        {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
        <p className="text-text-muted">Загрузка...</p>
      </div>
    );
  }

  const next = NEXT_STATUSES[pkg.status] ?? [];

  return (
    <div className="space-y-4">
      <button
        type="button"
        className="text-sm text-primary hover:underline"
        onClick={() => navigate("/ladya/packages")}
      >
        ← К списку пакетов
      </button>
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      <div className="rounded-xl border border-border bg-surface p-5">
        <p className="text-xs uppercase tracking-wide text-text-muted">
          {pkg.display_code}
        </p>
        <h2 className="mt-1 text-2xl font-bold text-text">{pkg.title}</h2>
        <p className="mt-2 text-sm text-text-muted whitespace-pre-wrap">
          {pkg.summary || "Без описания"}
        </p>
        <dl className="mt-4 grid gap-2 text-sm md:grid-cols-2">
          <div>
            <dt className="text-text-muted">Статус</dt>
            <dd className="font-medium">{STATUS_LABELS[pkg.status]}</dd>
          </div>
          <div>
            <dt className="text-text-muted">От → Кому</dt>
            <dd>
              {labTitle(pkg.from_laboratory)} → {labTitle(pkg.to_laboratory)}
            </dd>
          </div>
        </dl>
      </div>

      <div className="rounded-xl border border-border bg-surface p-4 space-y-3">
        <h3 className="text-sm font-semibold">Связь с Agent Ops (DeliveryTask)</h3>
        {!opsAvailable ? (
          <p className="text-sm text-text-muted">
            Agent Ops выключен в этом workspace — привязка недоступна. Включите
            модуль на странице Agent Ops.
          </p>
        ) : (
          <>
            {linkedTask ? (
              <div className="rounded-lg border border-border/60 bg-cream/40 px-3 py-2 text-sm">
                <div className="font-medium">
                  #{linkedTask.id} · {linkedTask.title}
                </div>
                <div className="mt-1 text-text-muted">
                  Статус: {linkedTask.status_label ?? linkedTask.status}
                  {linkedTask.assignee_email
                    ? ` · ${linkedTask.assignee_email}`
                    : ""}
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Link
                    to="/agent-ops"
                    className="rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-cream"
                  >
                    Открыть Agent Ops
                  </Link>
                  <button
                    type="button"
                    className="rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-cream"
                    onClick={() => void onUnlinkTask()}
                  >
                    Отвязать
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-text-muted">
                Пакет ещё не связан с задачей агентов. Можно создать новую
                DeliveryTask из пакета или привязать существующую — без
                auto-claim; агенты берут работу только через inbox/handoff.
              </p>
            )}
            <div className="flex flex-wrap items-center gap-2">
              {!linkedTask && (
                <button
                  type="button"
                  className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white"
                  onClick={() => void onCreateDeliveryTask()}
                >
                  Создать задачу Agent Ops
                </button>
              )}
              <select
                className="min-w-[16rem] flex-1 rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                value={taskPick}
                onChange={(e) =>
                  setTaskPick(e.target.value === "" ? "" : Number(e.target.value))
                }
              >
                <option value="">Выберите DeliveryTask…</option>
                {deliveryTasks.map((task) => (
                  <option key={task.id} value={task.id}>
                    #{task.id} · {task.title} ({task.status})
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-cream disabled:opacity-50"
                disabled={taskPick === ""}
                onClick={() => void onLinkTask()}
              >
                Привязать
              </button>
            </div>
          </>
        )}
      </div>

      <div className="rounded-xl border border-border bg-surface p-4 space-y-3">
        <h3 className="text-sm font-semibold">Передать в лабораторию</h3>
        <p className="text-xs text-text-muted">
          Из статусов accepted / in_progress / returned. Пишет событие в историю.
        </p>
        <div className="flex flex-wrap gap-2">
          <select
            className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
            value={transferLab}
            onChange={(e) =>
              setTransferLab(e.target.value === "" ? "" : Number(e.target.value))
            }
          >
            <option value="">Целевая лаборатория</option>
            {labs
              .filter((lab) => lab.is_active && lab.id !== pkg.to_laboratory)
              .map((lab) => (
                <option key={lab.id} value={lab.id}>
                  {lab.title}
                </option>
              ))}
          </select>
          <input
            className="min-w-[12rem] flex-1 rounded-lg border border-border bg-cream px-3 py-2 text-sm"
            placeholder="Причина передачи"
            value={transferReason}
            onChange={(e) => setTransferReason(e.target.value)}
          />
          <button
            type="button"
            className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
            disabled={transferLab === ""}
            onClick={() => void onTransfer()}
          >
            Передать
          </button>
        </div>
      </div>

      {next.length > 0 && (
        <div className="rounded-xl border border-border bg-surface p-4 space-y-3">
          <h3 className="text-sm font-semibold">Смена статуса</h3>
          <input
            className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
            placeholder="Причина / комментарий (необязательно)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            {next.map((status) => (
              <button
                key={status}
                type="button"
                className="rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-cream"
                onClick={() => void onTransition(status)}
              >
                → {STATUS_LABELS[status]}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-border bg-surface p-4 space-y-3">
        <h3 className="text-sm font-semibold">Файлы</h3>
        <p className="text-xs text-text-muted">
          Лимит {Math.round(packageMaxBytes / (1024 * 1024))} МБ. Hash считается
          потоково на сервере.
        </p>
        <input
          type="file"
          disabled={uploading}
          onChange={(e) => void onUpload(e.target.files?.[0] ?? null)}
        />
        {uploading && <p className="text-sm text-text-muted">Загрузка…</p>}
        <ul className="space-y-2 text-sm">
          {pkg.files.map((file) => (
            <li key={file.id} className="rounded-lg border border-border/60 px-3 py-2">
              <div className="font-medium">{file.original_name}</div>
              <div className="break-all text-xs text-text-muted">
                sha256: {file.sha256} · {file.size} байт
              </div>
            </li>
          ))}
          {pkg.files.length === 0 && (
            <li className="text-text-muted">Файлов пока нет</li>
          )}
        </ul>
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <button
            type="button"
            className="rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-cream"
            onClick={() => void onBuildManifest()}
          >
            Собрать манифест
          </button>
          {pkg.manifest_sha256 && (
            <span className="break-all text-xs text-text-muted">
              manifest_sha256: {pkg.manifest_sha256}
            </span>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
        <h3 className="text-sm font-semibold">История статусов</h3>
        {pkg.status_events.map((event) => (
          <div key={event.id} className="text-sm text-text-muted">
            {new Date(event.created_at).toLocaleString("ru-RU")}:{" "}
            {event.from_status || "—"} → {event.to_status}
            {event.reason ? ` — ${event.reason}` : ""}
          </div>
        ))}
      </div>
    </div>
  );
}

function LabDetailPanel() {
  const { labId } = useParams();
  const api = useLadyaApi();
  const navigate = useNavigate();
  const [lab, setLab] = useState<Laboratory | null>(null);
  const [packages, setPackages] = useState<LadyaPackage[]>([]);
  const [direction, setDirection] = useState("all");
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState("");
  const id = Number(labId);

  const load = useCallback(async () => {
    if (!api || !Number.isFinite(id)) return;
    try {
      const data = await api.listLabPackages(id, {
        direction,
        status: statusFilter || undefined,
      });
      setLab(data.laboratory);
      setPackages(data.packages);
      setError("");
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить лабораторию"));
    }
  }, [api, direction, id, statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!Number.isFinite(id)) {
    return <Navigate to="/ladya/labs" replace />;
  }

  return (
    <div className="space-y-4">
      <button
        type="button"
        className="text-sm text-primary hover:underline"
        onClick={() => navigate("/ladya/labs")}
      >
        ← К лабораториям
      </button>
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      {lab && (
        <div className="rounded-xl border border-border bg-surface p-5">
          <h2 className="text-2xl font-bold text-text">{lab.title}</h2>
          <p className="mt-1 text-sm text-text-muted">
            {lab.slug} ·{" "}
            {LAB_KINDS.find((k) => k.value === lab.kind)?.label ?? lab.kind} ·{" "}
            {lab.is_active ? "активна" : "неактивна"}
          </p>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <select
          className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
        >
          <option value="all">Все пакеты</option>
          <option value="incoming">Входящие</option>
          <option value="outgoing">Исходящие</option>
        </select>
        <select
          className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">Все статусы</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <ul className="space-y-2">
        {packages.map((pkg) => (
          <li key={pkg.id}>
            <Link
              to={`/ladya/packages/${pkg.id}`}
              className="block rounded-lg border border-border bg-surface px-4 py-3 text-sm hover:bg-cream"
            >
              {pkg.display_code} · {pkg.title} · {STATUS_LABELS[pkg.status]}
            </Link>
          </li>
        ))}
        {packages.length === 0 && (
          <li className="text-sm text-text-muted">Пакетов нет</li>
        )}
      </ul>
    </div>
  );
}

function IntakePanel() {
  const api = useLadyaApi();
  const navigate = useNavigate();
  const { workspaceEpoch } = useWorkspace();
  const [rows, setRows] = useState<IntakeRequest[]>([]);
  const [labs, setLabs] = useState<Laboratory[]>([]);
  const [error, setError] = useState("");
  const [body, setBody] = useState("");
  const [contact, setContact] = useState("");
  const [toLab, setToLab] = useState<number | "">("");
  const [queueFilter, setQueueFilter] = useState<"" | "new" | "triaged">("new");

  const load = useCallback(async () => {
    if (!api) return;
    try {
      const [intakeRows, labRows] = await Promise.all([
        api.listIntake(queueFilter || undefined),
        api.listLaboratories(),
      ]);
      setRows(intakeRows);
      setLabs(labRows);
      setToLab((current) => {
        if (current !== "") return current;
        const central = labRows.find((l) => l.kind === "central_lad" && l.is_active);
        return central?.id ?? "";
      });
      setError("");
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить обращения"));
    }
  }, [api, queueFilter]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const onCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!api) return;
    try {
      await api.createIntake({ body, contact, source: "web_form" });
      setBody("");
      setContact("");
      setQueueFilter("new");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось отправить обращение"));
    }
  };

  const onTriage = async (id: number, status: "triaged" | "closed") => {
    if (!api) return;
    try {
      await api.triageIntake(id, status);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось обновить обращение"));
    }
  };

  const onConvert = async (id: number) => {
    if (!api) return;
    if (toLab === "") {
      setError("Выберите лабораторию-получателя (обычно central_lad)");
      return;
    }
    try {
      const result = await api.convertIntake(id, {
        to_laboratory: toLab,
      });
      navigate(`/ladya/packages/${result.package.id}`);
    } catch (err) {
      setError(parseApiError(err, "Не удалось преобразовать в пакет"));
    }
  };

  return (
    <div className="space-y-4">
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      <p className="text-sm text-text-muted">
        Человек пишет во Вход; ЛАД принимает обращение и превращает его в Package.
        Внутренние пакеты здесь не показываются.
      </p>
      <form
        onSubmit={(e) => void onCreate(e)}
        className="space-y-3 rounded-xl border border-border bg-surface p-4"
      >
        <h3 className="text-sm font-semibold">Форма входа в ЛАД</h3>
        <textarea
          className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          rows={4}
          placeholder="Текст обращения"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          required
        />
        <input
          className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
          placeholder="Контакт (email / telegram)"
          value={contact}
          onChange={(e) => setContact(e.target.value)}
        />
        <button
          type="submit"
          className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white"
        >
          Отправить
        </button>
      </form>

      <div className="rounded-xl border border-border bg-surface p-4 space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <h3 className="text-sm font-semibold">Очередь обращений</h3>
          <select
            className="rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
            value={queueFilter}
            onChange={(e) =>
              setQueueFilter(e.target.value as "" | "new" | "triaged")
            }
          >
            <option value="new">new</option>
            <option value="triaged">triaged</option>
            <option value="">все</option>
          </select>
          <select
            className="rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
            value={toLab}
            onChange={(e) =>
              setToLab(e.target.value === "" ? "" : Number(e.target.value))
            }
          >
            <option value="">Лаборатория для convert (обязательно)</option>
            {labs.map((lab) => (
              <option key={lab.id} value={lab.id}>
                {lab.title}
                {lab.kind === "central_lad" ? " ★" : ""}
              </option>
            ))}
          </select>
        </div>
        <ul className="space-y-3">
          {rows.map((row) => (
            <li
              key={row.id}
              className="rounded-lg border border-border/60 px-3 py-3 text-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="font-medium">
                    #{row.id} · {row.status}
                  </div>
                  <div className="mt-1 whitespace-pre-wrap text-text-muted">
                    {row.body}
                  </div>
                  {row.contact && (
                    <div className="mt-1 text-xs text-text-muted">
                      Контакт: {row.contact}
                    </div>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {row.status === "new" && (
                    <>
                      <button
                        type="button"
                        className="rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-cream"
                        onClick={() => void onTriage(row.id, "triaged")}
                      >
                        Triage
                      </button>
                      <button
                        type="button"
                        className="rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-cream"
                        onClick={() => void onTriage(row.id, "closed")}
                      >
                        Close
                      </button>
                    </>
                  )}
                  {(row.status === "new" || row.status === "triaged") && (
                    <button
                      type="button"
                      className="rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-cream"
                      onClick={() => void onConvert(row.id)}
                    >
                      Convert → Package
                    </button>
                  )}
                  {row.package && (
                    <Link
                      to={`/ladya/packages/${row.package}`}
                      className="rounded-lg border border-border px-3 py-1.5 text-xs text-primary hover:bg-cream"
                    >
                      Пакет #{row.package}
                    </Link>
                  )}
                </div>
              </div>
            </li>
          ))}
          {rows.length === 0 && (
            <li className="text-text-muted">Обращений пока нет</li>
          )}
        </ul>
      </div>
    </div>
  );
}

export function LadyaPage() {
  const api = useLadyaApi();
  const { theme } = useTheme();
  const { workspaceEpoch, activeWorkspace } = useWorkspace();
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  const isDark = theme === "dark";
  const logoMark = isDark ? "/ladya/logo-dark-mark.png" : "/ladya/logo-mark.png";
  const logoSvg = isDark ? "/ladya/logo-dark-mark.svg" : "/ladya/logo-mark.svg";
  const heroSrc = isDark ? "/ladya/hero-dark.jpg" : "/ladya/hero-light.jpg";

  useEffect(() => {
    if (!api) return;
    void api
      .getSettings()
      .then((settings) => setEnabled(settings.ladya_hub_enabled))
      .catch((err) =>
        setError(parseApiError(err, "Не удалось проверить флаг Ладьи")),
      );
  }, [api, workspaceEpoch]);

  if (enabled === false) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <img src={logoSvg} alt="" className="h-10 w-10" aria-hidden />
          <h1 className="text-3xl font-bold text-text">Ладья</h1>
        </div>
        <p className="text-sm text-text-muted">
          Контур выключен для workspace
          {activeWorkspace ? ` «${activeWorkspace.name}»` : ""}. Включите флаг в
          Настройках → модуль «Ладья».
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-2xl border border-border bg-surface">
        <div className="relative min-h-[9.5rem] md:min-h-[11rem]">
          <img
            src={heroSrc}
            alt=""
            className="absolute inset-0 h-full w-full object-cover object-center"
          />
          <div
            className={[
              "absolute inset-0 bg-gradient-to-r from-surface via-surface/90",
              isDark ? "to-surface/55" : "to-surface/40",
            ].join(" ")}
          />
          <div className="relative flex items-center gap-4 px-5 py-6 md:px-7">
            <img
              src={logoMark}
              alt="Ладья"
              className="h-16 w-16 shrink-0 drop-shadow-sm md:h-20 md:w-20"
            />
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-primary">
                Контур координации
              </p>
              <h1 className="text-3xl font-bold text-text">Ладья</h1>
              <p className="mt-1 max-w-xl text-sm text-text-muted">
                Операционный контур лабораторий: пакеты работы, файлы, вход
                людей. Не приёмка Lab-0 — координация обмена.
              </p>
            </div>
          </div>
        </div>
      </section>
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      <SubNav />
      <Routes>
        <Route index element={<Navigate to="packages" replace />} />
        <Route path="labs" element={<LabsPanel />} />
        <Route path="labs/:labId" element={<LabDetailPanel />} />
        <Route path="packages" element={<PackagesPanel />} />
        <Route path="packages/:packageId" element={<PackageDetailPanel />} />
        <Route path="intake" element={<IntakePanel />} />
      </Routes>
    </div>
  );
}
