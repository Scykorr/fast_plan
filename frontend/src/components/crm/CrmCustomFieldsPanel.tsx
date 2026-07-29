import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../../api/errors";
import { useCrmApi } from "../../hooks/useCrmApi";

export type CustomFieldTarget = "organization" | "person" | "deal" | "lead";

type FieldDef = {
  id: number;
  target: string;
  key: string;
  label: string;
  field_type: string;
  options: string[];
  required: boolean;
  position: number;
  is_active: boolean;
};

type Props = {
  target: CustomFieldTarget;
  entityId: number | null;
  /** Allow creating new definitions inline */
  allowManage?: boolean;
};

export function CrmCustomFieldsPanel({
  target,
  entityId,
  allowManage = true,
}: Props) {
  const crmApi = useCrmApi();
  const [defs, setDefs] = useState<FieldDef[]>([]);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [draft, setDraft] = useState({
    key: "",
    label: "",
    field_type: "text",
    options: "",
  });

  const load = useCallback(async () => {
    if (!crmApi || !entityId) return;
    try {
      const data = await crmApi.getEntityCustomFields(target, entityId);
      setDefs(data.definitions || []);
      setValues(data.values || {});
    } catch (err) {
      setError(parseApiError(err));
    }
  }, [crmApi, entityId, target]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    if (!crmApi || !entityId) return;
    try {
      const res = await crmApi.putEntityCustomFields(target, entityId, values);
      setValues(res.values || {});
      setMessage("Поля сохранены");
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const createDef = async () => {
    if (!crmApi || !draft.label.trim() || !draft.key.trim()) return;
    try {
      await crmApi.createCustomField({
        target,
        key: draft.key.trim(),
        label: draft.label.trim(),
        field_type: draft.field_type,
        options: draft.options
          ? draft.options.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
      });
      setDraft({ key: "", label: "", field_type: "text", options: "" });
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  if (!entityId) return null;

  return (
    <div className="space-y-2 rounded-lg border border-border bg-cream/40 p-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-text-muted">
          Custom fields
        </h3>
        {defs.length > 0 && (
          <button
            type="button"
            className="rounded border border-border px-2 py-0.5 text-xs"
            onClick={() => void save()}
          >
            Сохранить
          </button>
        )}
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
      {message && <p className="text-xs text-secondary">{message}</p>}
      {defs.length === 0 ? (
        <p className="text-xs text-text-muted">Нет полей для этой карточки.</p>
      ) : (
        <div className="space-y-2">
          {defs.map((d) => (
            <label key={d.id} className="block text-xs">
              <span className="text-text-muted">
                {d.label}
                {d.required ? " *" : ""}
              </span>
              {d.field_type === "bool" ? (
                <input
                  type="checkbox"
                  className="ml-2"
                  checked={Boolean(values[d.key])}
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, [d.key]: e.target.checked }))
                  }
                />
              ) : d.field_type === "select" ? (
                <select
                  className="mt-0.5 w-full rounded border border-border bg-surface px-2 py-1"
                  value={String(values[d.key] ?? "")}
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, [d.key]: e.target.value }))
                  }
                >
                  <option value="">—</option>
                  {(d.options || []).map((o) => (
                    <option key={o} value={o}>
                      {o}
                    </option>
                  ))}
                </select>
              ) : d.field_type === "number" ? (
                <input
                  type="number"
                  className="mt-0.5 w-full rounded border border-border bg-surface px-2 py-1"
                  value={values[d.key] == null ? "" : String(values[d.key])}
                  onChange={(e) =>
                    setValues((prev) => ({
                      ...prev,
                      [d.key]: e.target.value === "" ? null : Number(e.target.value),
                    }))
                  }
                />
              ) : d.field_type === "date" ? (
                <input
                  type="date"
                  className="mt-0.5 w-full rounded border border-border bg-surface px-2 py-1"
                  value={String(values[d.key] ?? "")}
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, [d.key]: e.target.value }))
                  }
                />
              ) : (
                <input
                  className="mt-0.5 w-full rounded border border-border bg-surface px-2 py-1"
                  value={String(values[d.key] ?? "")}
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, [d.key]: e.target.value }))
                  }
                />
              )}
            </label>
          ))}
        </div>
      )}
      {allowManage && (
        <details className="text-xs">
          <summary className="cursor-pointer text-text-muted">Добавить поле</summary>
          <div className="mt-2 flex flex-wrap gap-1">
            <input
              placeholder="key"
              className="w-24 rounded border border-border bg-surface px-2 py-1"
              value={draft.key}
              onChange={(e) => setDraft({ ...draft, key: e.target.value })}
            />
            <input
              placeholder="label"
              className="min-w-[8rem] flex-1 rounded border border-border bg-surface px-2 py-1"
              value={draft.label}
              onChange={(e) => setDraft({ ...draft, label: e.target.value })}
            />
            <select
              className="rounded border border-border bg-surface px-2 py-1"
              value={draft.field_type}
              onChange={(e) => setDraft({ ...draft, field_type: e.target.value })}
            >
              <option value="text">text</option>
              <option value="number">number</option>
              <option value="bool">bool</option>
              <option value="date">date</option>
              <option value="select">select</option>
            </select>
            {draft.field_type === "select" && (
              <input
                placeholder="options a,b,c"
                className="w-full rounded border border-border bg-surface px-2 py-1"
                value={draft.options}
                onChange={(e) => setDraft({ ...draft, options: e.target.value })}
              />
            )}
            <button
              type="button"
              className="rounded border border-border px-2 py-1"
              onClick={() => void createDef()}
            >
              Создать
            </button>
          </div>
        </details>
      )}
    </div>
  );
}
