import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useMemo, useRef, useState } from "react";

import { GlossaryText, TermHint } from "./TermHint";
import { NotificationBell } from "./NotificationBell";
import { FxSettingsLoader } from "./FxSettingsLoader";
import { ThemeToggle } from "./ThemeToggle";
import { GlobalSearchBar } from "./search/GlobalSearchBar";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../context/LocaleContext";
import { useWorkspace } from "../context/WorkspaceContext";
import { useWorkspaceEvents } from "../hooks/useWorkspaceEvents";
import { APP_VERSION } from "../version";

type NavItem = {
  to: string;
  labelKey?:
    | "dashboard"
    | "portfolio"
    | "clients"
    | "deals"
    | "leads"
    | "automations"
    | "processes"
    | "processTasks"
    | "agentOps"
    | "crmAi"
    | "crmCommerce"
    | "crmAnalytics"
    | "crmTasks"
    | "projects"
    | "myTasks"
    | "calendar"
    | "finance"
    | "audit"
    | "administration"
    | "settings";
  label?: string;
  term?: "capacity" | "kanban";
  end?: boolean;
};

type NavGroupId = "overview" | "projects" | "crm" | "process" | "system";

type NavGroup = {
  id: NavGroupId;
  labelKey: "navOverview" | "navProjects" | "navCrm" | "navProcess" | "navSystem";
  items: NavItem[];
};

const navGroups: NavGroup[] = [
  {
    id: "overview",
    labelKey: "navOverview",
    items: [
      { to: "/", labelKey: "dashboard", end: true },
      { to: "/portfolio", labelKey: "portfolio" },
      { to: "/calendar", labelKey: "calendar" },
    ],
  },
  {
    id: "projects",
    labelKey: "navProjects",
    items: [
      { to: "/projects", labelKey: "projects" },
      { to: "/tasks", labelKey: "myTasks" },
      { to: "/capacity", label: "Capacity", term: "capacity" },
      { to: "/kanban", label: "Kanban", term: "kanban" },
    ],
  },
  {
    id: "crm",
    labelKey: "navCrm",
    items: [
      { to: "/clients", labelKey: "clients" },
      { to: "/deals", labelKey: "deals" },
      { to: "/leads", labelKey: "leads" },
      { to: "/crm-tasks", labelKey: "crmTasks" },
      { to: "/crm-commerce", labelKey: "crmCommerce" },
      { to: "/crm-analytics", labelKey: "crmAnalytics" },
      { to: "/crm-ai", labelKey: "crmAi" },
    ],
  },
  {
    id: "process",
    labelKey: "navProcess",
    items: [
      { to: "/processes", labelKey: "processes" },
      { to: "/process-tasks", labelKey: "processTasks" },
      { to: "/automations", labelKey: "automations" },
      { to: "/agent-ops", labelKey: "agentOps" },
    ],
  },
  {
    id: "system",
    labelKey: "navSystem",
    items: [
      { to: "/finance", labelKey: "finance" },
      { to: "/audit", labelKey: "audit" },
      { to: "/administration", labelKey: "administration" },
      { to: "/settings", labelKey: "settings" },
    ],
  },
];

function pathMatches(pathname: string, item: NavItem): boolean {
  if (item.end) {
    return pathname === item.to;
  }
  if (item.to === "/") {
    return pathname === "/";
  }
  return pathname === item.to || pathname.startsWith(`${item.to}/`);
}

function groupContainsPath(group: NavGroup, pathname: string): boolean {
  return group.items.some((item) => pathMatches(pathname, item));
}

function NavItemLink({
  item,
  onNavigate,
}: {
  item: NavItem;
  onNavigate?: () => void;
}) {
  const { t } = useLocale();
  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onNavigate}
      className={({ isActive }) =>
        [
          "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "border-l-4 border-primary bg-cream pl-2 text-primary"
            : "text-text-muted hover:bg-cream hover:text-text",
        ].join(" ")
      }
    >
      {item.label && item.term ? (
        <TermHint term={item.term}>{item.label}</TermHint>
      ) : item.labelKey ? (
        <GlossaryText text={t(item.labelKey)} />
      ) : (
        item.label
      )}
    </NavLink>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth();
  const { t } = useLocale();
  const { workspaces, activeWorkspace, switchWorkspace } = useWorkspace();
  const { pathname } = useLocation();
  const [switching, setSwitching] = useState(false);
  const [openGroups, setOpenGroups] = useState<Set<NavGroupId>>(() => {
    const active = navGroups.find((group) => groupContainsPath(group, pathname));
    return new Set(active ? [active.id] : ["overview"]);
  });

  const activeGroupId = useMemo(
    () => navGroups.find((group) => groupContainsPath(group, pathname))?.id,
    [pathname],
  );

  useEffect(() => {
    if (!activeGroupId) {
      return;
    }
    setOpenGroups((current) => {
      if (current.has(activeGroupId)) {
        return current;
      }
      const next = new Set(current);
      next.add(activeGroupId);
      return next;
    });
  }, [activeGroupId]);

  const toggleGroup = (id: NavGroupId) => {
    setOpenGroups((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

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
      <div className="mb-6 px-2">
        <h1 className="text-xl font-bold text-primary">Fast Plan</h1>
        <p className="mt-1 text-sm text-text-muted">{t("planner")}</p>
        <p className="mt-1 text-xs text-text-muted" title="Версия продукта">
          v{APP_VERSION}
        </p>
        {workspaces.length > 0 && (
          <label className="mt-3 block text-xs text-text-muted">
            <TermHint term="workspace">Workspace</TermHint>
            <select
              className="mt-1 w-full rounded-lg border border-border bg-cream px-2 py-1.5 text-sm text-text"
              value={activeWorkspace?.id ?? ""}
              disabled={switching || workspaces.length < 2}
              onChange={(event) => void handleSwitch(Number(event.target.value))}
              aria-label="Выбор рабочего пространства (workspace)"
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

      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto pr-1">
        {navGroups.map((group) => {
          const open = openGroups.has(group.id);
          const panelId = `nav-group-${group.id}`;
          return (
            <div key={group.id} className="mb-1">
              <button
                type="button"
                aria-expanded={open}
                aria-controls={panelId}
                onClick={() => toggleGroup(group.id)}
                className={[
                  "flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide transition-colors",
                  activeGroupId === group.id
                    ? "text-primary"
                    : "text-text-muted hover:bg-cream hover:text-text",
                ].join(" ")}
              >
                <span>{t(group.labelKey)}</span>
                <span className="text-[10px]" aria-hidden>
                  {open ? "▾" : "▸"}
                </span>
              </button>
              {open && (
                <div id={panelId} className="mt-0.5 flex flex-col gap-0.5 pl-1">
                  {group.items.map((item) => (
                    <NavItemLink
                      key={String(item.to)}
                      item={item}
                      onNavigate={onNavigate}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
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
    </div>
  );
}
