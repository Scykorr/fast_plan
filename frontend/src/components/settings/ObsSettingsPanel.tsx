import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../../api/errors";
import type { ObsRole, OrgUnit } from "../../api/workspace";
import { ErrorMessage } from "../ErrorMessage";
import { useWorkspaceApi } from "../../hooks/useWorkspaceApi";
import { useWorkspace } from "../../context/WorkspaceContext";

function flattenUnits(
  nodes: OrgUnit[],
  depth = 0,
): Array<OrgUnit & { depth: number }> {
  const out: Array<OrgUnit & { depth: number }> = [];
  for (const node of nodes) {
    out.push({ ...node, depth });
    if (node.children?.length) {
      out.push(...flattenUnits(node.children, depth + 1));
    }
  }
  return out;
}

export function ObsSettingsPanel() {
  const api = useWorkspaceApi();
  const { workspaceEpoch } = useWorkspace();
  const [tree, setTree] = useState<OrgUnit[]>([]);
  const [roles, setRoles] = useState<ObsRole[]>([]);
  const [error, setError] = useState("");
  const [unitName, setUnitName] = useState("");
  const [unitParentId, setUnitParentId] = useState<number | "">("");
  const [roleName, setRoleName] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!api) return;
    try {
      const [units, roleRows] = await Promise.all([
        api.getOrgUnits(),
        api.getObsRoles(),
      ]);
      setTree(units);
      setRoles(roleRows);
      setError("");
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить OBS"));
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const flat = flattenUnits(tree);

  const addUnit = async () => {
    if (!api || !unitName.trim()) return;
    setBusy(true);
    try {
      await api.createOrgUnit({
        name: unitName.trim(),
        parent_id: unitParentId === "" ? null : Number(unitParentId),
      });
      setUnitName("");
      setUnitParentId("");
      await load();
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const removeUnit = async (id: number) => {
    if (!api || !window.confirm("Удалить подразделение и дочерние?")) return;
    setBusy(true);
    try {
      await api.deleteOrgUnit(id);
      await load();
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const addRole = async () => {
    if (!api || !roleName.trim()) return;
    setBusy(true);
    try {
      await api.createObsRole({ name: roleName.trim() });
      setRoleName("");
      await load();
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const removeRole = async (id: number) => {
    if (!api || !window.confirm("Удалить OBS-роль?")) return;
    setBusy(true);
    try {
      await api.deleteObsRole(id);
      await load();
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="rounded-xl border border-border bg-surface p-5">
      <h2 className="text-lg font-semibold text-text">OBS / оргструктура</h2>
      <p className="mt-1 text-sm text-text-muted">
        Подразделения и должности для привязки к WBS (не ACL-роли workspace).
      </p>
      <ErrorMessage message={error} onDismiss={() => setError("")} />

      <div className="mt-4 grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="text-sm font-semibold text-text">Подразделения</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            <input
              value={unitName}
              onChange={(e) => setUnitName(e.target.value)}
              placeholder="Название (напр. Backend)"
              className="min-w-[10rem] flex-1 rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
            />
            <select
              value={unitParentId}
              onChange={(e) =>
                setUnitParentId(e.target.value ? Number(e.target.value) : "")
              }
              className="rounded-lg border border-border bg-cream px-2 py-1.5 text-sm"
            >
              <option value="">Корень</option>
              {flat.map((u) => (
                <option key={u.id} value={u.id}>
                  {"—".repeat(u.depth)} {u.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={busy || !unitName.trim()}
              onClick={() => void addUnit()}
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              Добавить
            </button>
          </div>
          <ul className="mt-3 space-y-1 text-sm">
            {flat.map((u) => (
              <li
                key={u.id}
                className="flex items-center justify-between gap-2 rounded-lg border border-border px-2 py-1.5"
                style={{ paddingLeft: `${0.5 + u.depth * 0.75}rem` }}
              >
                <span className="text-text">
                  {u.code ? `${u.code} · ` : ""}
                  {u.name}
                </span>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void removeUnit(u.id)}
                  className="text-xs text-danger"
                >
                  Удалить
                </button>
              </li>
            ))}
            {flat.length === 0 && (
              <li className="text-text-muted">Пока нет подразделений</li>
            )}
          </ul>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-text">OBS-роли (должности)</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            <input
              value={roleName}
              onChange={(e) => setRoleName(e.target.value)}
              placeholder="Напр. Tech Lead"
              className="min-w-[10rem] flex-1 rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
            />
            <button
              type="button"
              disabled={busy || !roleName.trim()}
              onClick={() => void addRole()}
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              Добавить
            </button>
          </div>
          <ul className="mt-3 space-y-1 text-sm">
            {roles.map((r) => (
              <li
                key={r.id}
                className="flex items-center justify-between gap-2 rounded-lg border border-border px-2 py-1.5"
              >
                <span className="text-text">{r.name}</span>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void removeRole(r.id)}
                  className="text-xs text-danger"
                >
                  Удалить
                </button>
              </li>
            ))}
            {roles.length === 0 && (
              <li className="text-text-muted">Пока нет ролей</li>
            )}
          </ul>
        </div>
      </div>
    </section>
  );
}
