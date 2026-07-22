import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useRef, useState } from "react";

import { NotificationBell } from "./NotificationBell";
import { FxSettingsLoader } from "./FxSettingsLoader";
import { PwaUpdatePrompt } from "./PwaUpdatePrompt";
import { ThemeToggle } from "./ThemeToggle";
import { GlobalSearchBar } from "./search/GlobalSearchBar";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../context/LocaleContext";
import { useWorkspace } from "../context/WorkspaceContext";
import { useWorkspaceEvents } from "../hooks/useWorkspaceEvents";
import { APP_VERSION } from "../version";

const navItems = [
  { to: "/", labelKey: "dashboard", end: true },
  { to: "/portfolio", labelKey: "portfolio" },
  { to: "/clients", labelKey: "clients" },
  { to: "/deals", labelKey: "deals" },
  { to: "/leads", labelKey: "leads" },
  { to: "/automations", labelKey: "automations" },
  { to: "/projects", labelKey: "projects" },
  { to: "/tasks", labelKey: "myTasks" },
  { to: "/capacity", label: "Capacity" },
  { to: "/kanban", label: "Kanban" },
  { to: "/calendar", labelKey: "calendar" },
  { to: "/finance", labelKey: "finance" },
  { to: "/audit", labelKey: "audit" },
  { to: "/administration", labelKey: "administration" },
  { to: "/settings", labelKey: "settings" },
] as const;

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth();
  const { t } = useLocale();
  const { workspaces, activeWorkspace, switchWorkspace } = useWorkspace();
  const [switching, setSwitching] = useState(false);

  const handleSwitch = async (workspaceId: number) => {
    if (workspaceId === activeWorkspace?.id) {
      return;
    }
    setSwitching(true);
    try {
      await switchWorkspace(workspaceId);
    } finally {
      setSwitching(false);
    }
  };

  return (
    <>
      <div className="mb-8 px-2">
        <h1 className="text-xl font-bold text-primary">Fast Plan</h1>
        <p className="mt-1 text-sm text-text-muted">{t("planner")}</p>
        <p className="mt-1 text-xs text-text-muted" title="Версия продукта">
          v{APP_VERSION}
        </p>
        {workspaces.length > 0 && (
          <label className="mt-3 block text-xs text-text-muted">
            Workspace
            <select
              className="mt-1 w-full rounded-lg border border-border bg-cream px-2 py-1.5 text-sm text-text"
              value={activeWorkspace?.id ?? ""}
              disabled={switching || workspaces.length < 2}
              onChange={(event) => void handleSwitch(Number(event.target.value))}
              aria-label="Выбор workspace"
            >
              {workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name} ({workspace.role})
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={"end" in item ? item.end : undefined}
            onClick={onNavigate}
            className={({ isActive }) =>
              [
                "rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "border-l-4 border-primary bg-cream pl-2 text-primary"
                  : "text-text-muted hover:bg-cream hover:text-text",
              ].join(" ")
            }
          >
            {"labelKey" in item ? t(item.labelKey) : item.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto border-t border-border pt-4">
        <p className="truncate px-2 text-sm font-medium">{user?.email}</p>
        <button
          type="button"
          onClick={() => void logout()}
          className="mt-2 w-full rounded-lg px-3 py-2 text-left text-sm text-text-muted transition-colors hover:bg-cream hover:text-primary"
        >
          {t("logout")}
        </button>
      </div>
    </>
  );
}

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { workspaceEpoch, activeWorkspace } = useWorkspace();
  const { isAuthenticated } = useAuth();
  const { t } = useLocale();
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<number | null>(null);

  useWorkspaceEvents(isAuthenticated && Boolean(activeWorkspace), () => {
    setToast(t("dataUpdated"));
    if (toastTimer.current) {
      window.clearTimeout(toastTimer.current);
    }
    toastTimer.current = window.setTimeout(() => setToast(null), 3000);
  });

  useEffect(() => {
    return () => {
      if (toastTimer.current) {
        window.clearTimeout(toastTimer.current);
      }
    };
  }, []);

  return (
    <div className="flex min-h-screen">
      <FxSettingsLoader />
      {toast && (
        <div
          role="status"
          className="fixed bottom-4 right-4 z-[60] rounded-lg bg-text px-4 py-2 text-sm font-medium text-white shadow-lg"
        >
          {toast}
        </div>
      )}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-surface px-4 py-6 md:flex">
        <SidebarContent />
      </aside>

      {mobileOpen && (
        <button
          type="button"
          aria-label="Закрыть меню"
          className="fixed inset-0 z-40 bg-black/30 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={[
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-surface px-4 py-6 transition-transform md:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        ].join(" ")}
      >
        <SidebarContent onNavigate={() => setMobileOpen(false)} />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-border bg-surface px-4 py-3 md:hidden">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="rounded-lg px-3 py-2 text-sm font-medium text-text hover:bg-cream"
            aria-label="Открыть меню"
          >
            ☰ Меню
          </button>
          <div className="flex min-w-0 flex-1 items-center justify-end gap-2">
            <GlobalSearchBar />
            <ThemeToggle />
            <NotificationBell />
            <span className="shrink-0 text-sm font-semibold text-primary">Fast Plan</span>
          </div>
        </header>

        <header className="hidden items-center justify-end gap-3 border-b border-border bg-surface px-8 py-3 md:flex">
          <GlobalSearchBar />
          <ThemeToggle />
          <NotificationBell />
        </header>

        <main className="flex-1 overflow-auto p-4 md:p-8" key={workspaceEpoch}>
          <Outlet />
        </main>
      </div>
      <PwaUpdatePrompt />
    </div>
  );
}
