import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../../api/errors";
import { useCrmApi } from "../../hooks/useCrmApi";

export type SavedFilterRow = {
  id: number;
  target: string;
  name: string;
  params: Record<string, unknown>;
};

type Props = {
  target: "clients" | "deals" | "leads";
  currentParams: Record<string, unknown>;
  onApply: (params: Record<string, unknown>) => void;
};

export function CrmSavedFiltersBar({ target, currentParams, onApply }: Props) {
  const crmApi = useCrmApi();
  const [rows, setRows] = useState<SavedFilterRow[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!crmApi) return;
    try {
      const data = await crmApi.listSavedFilters(target);
      setRows(data);
    } catch (err) {
      setError(parseApiError(err));
    }
  }, [crmApi, target]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    if (!crmApi || !name.trim()) return;
    try {
      await crmApi.createSavedFilter({
        target,
        name: name.trim(),
        params: currentParams,
      });
      setName("");
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  const remove = async (id: number) => {
    if (!crmApi) return;
    try {
      await crmApi.deleteSavedFilter(id);
      await load();
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm">
      <span className="text-xs font-medium text-text-muted">Saved filters</span>
      <select
        className="rounded border border-border bg-cream px-2 py-1 text-xs"
        defaultValue=""
        onChange={(e) => {
          const id = Number(e.target.value);
          const row = rows.find((r) => r.id === id);
          if (row) onApply(row.params || {});
          e.target.value = "";
        }}
      >
        <option value="">Применить…</option>
        {rows.map((r) => (
          <option key={r.id} value={r.id}>
            {r.name}
          </option>
        ))}
      </select>
      <input
        className="w-36 rounded border border-border bg-cream px-2 py-1 text-xs"
        placeholder="Имя фильтра"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <button
        type="button"
        className="rounded border border-border px-2 py-1 text-xs"
        onClick={() => void save()}
      >
        Сохранить
      </button>
      {rows.length > 0 && (
        <button
          type="button"
          className="rounded border border-border px-2 py-1 text-xs text-text-muted"
          onClick={() => {
            const last = rows[0];
            if (last) void remove(last.id);
          }}
          title="Удалить первый в списке"
        >
          Удалить 1-й
        </button>
      )}
      {error && <span className="text-xs text-danger">{error}</span>}
    </div>
  );
}
