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
  PackageStatus,
} from "../api/ladya";
import { ErrorMessage } from "../components/ErrorMessage";
import { useWorkspace } from "../context/WorkspaceContext";
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
                <td className="px-4 py-3">{lab.title}</td>
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
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [fromLab, setFromLab] = useState<number | "">("");
  const [toLab, setToLab] = useState<number | "">("");

  const load = useCallback(async () => {
    if (!api) return;
    try {
      const [pkgRows, labRows] = await Promise.all([
        api.listPackages(),
        api.listLaboratories(),
      ]);
      setPackages(pkgRows);
      setLabs(labRows);
      setError("");
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить пакеты"));
    }
  }, [api]);

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
  const navigate = useNavigate();
  const [pkg, setPkg] = useState<LadyaPackage | null>(null);
  const [labs, setLabs] = useState<Laboratory[]>([]);
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
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить пакет"));
    }
  }, [api, id]);

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
    try {
      await api.uploadPackageFile(pkg.id, file);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить файл"));
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
        <input
          type="file"
          onChange={(e) => void onUpload(e.target.files?.[0] ?? null)}
        />
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

  const load = useCallback(async () => {
    if (!api) return;
    try {
      const [intakeRows, labRows] = await Promise.all([
        api.listIntake(),
        api.listLaboratories(),
      ]);
      setRows(intakeRows);
      setLabs(labRows);
      setError("");
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить обращения"));
    }
  }, [api]);

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
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось отправить обращение"));
    }
  };

  const onConvert = async (id: number) => {
    if (!api) return;
    try {
      const result = await api.convertIntake(id, {
        title: `Из обращения #${id}`,
        to_laboratory: toLab === "" ? null : toLab,
      });
      navigate(`/ladya/packages/${result.package.id}`);
    } catch (err) {
      setError(parseApiError(err, "Не удалось преобразовать в пакет"));
    }
  };

  return (
    <div className="space-y-4">
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
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
            value={toLab}
            onChange={(e) =>
              setToLab(e.target.value === "" ? "" : Number(e.target.value))
            }
          >
            <option value="">Лаборатория для convert</option>
            {labs.map((lab) => (
              <option key={lab.id} value={lab.id}>
                {lab.title}
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
                {row.status !== "converted" && row.status !== "closed" && (
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
                    className="text-xs text-primary hover:underline"
                  >
                    Пакет #{row.package}
                  </Link>
                )}
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
  const { workspaceEpoch, activeWorkspace } = useWorkspace();
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [error, setError] = useState("");

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
        <h1 className="text-3xl font-bold text-text">Ладья</h1>
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
      <div>
        <h1 className="text-3xl font-bold text-text">Ладья</h1>
        <p className="mt-1 text-sm text-text-muted">
          Операционный контур лабораторий: пакеты работы, файлы, вход людей
        </p>
      </div>
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      <SubNav />
      <Routes>
        <Route index element={<Navigate to="packages" replace />} />
        <Route path="labs" element={<LabsPanel />} />
        <Route path="packages" element={<PackagesPanel />} />
        <Route path="packages/:packageId" element={<PackageDetailPanel />} />
        <Route path="intake" element={<IntakePanel />} />
      </Routes>
    </div>
  );
}
