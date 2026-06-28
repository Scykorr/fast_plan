import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const navItems = [
  { to: "/", label: "Дашборд", end: true },
  { to: "/kanban", label: "Kanban" },
  { to: "/calendar", label: "Календарь" },
  { to: "/settings", label: "Настройки" },
];

export function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-64 flex-col border-r border-border bg-surface px-4 py-6">
        <div className="mb-8 px-2">
          <h1 className="text-xl font-bold text-primary">Fast Plan</h1>
          <p className="mt-1 text-sm text-text-muted">Ваш личный планировщик</p>
        </div>

        <nav className="flex flex-1 flex-col gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                [
                  "rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "border-l-4 border-primary bg-cream pl-2 text-primary"
                    : "text-text-muted hover:bg-cream hover:text-text",
                ].join(" ")
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto border-t border-border pt-4">
          <p className="truncate px-2 text-sm font-medium">{user?.email}</p>
          <button
            type="button"
            onClick={logout}
            className="mt-2 w-full rounded-lg px-3 py-2 text-left text-sm text-text-muted transition-colors hover:bg-cream hover:text-primary"
          >
            Выйти
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
