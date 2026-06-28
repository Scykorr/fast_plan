import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export function DashboardPage() {
  const { user } = useAuth();

  return (
    <div>
      <h1 className="text-3xl font-bold text-text">
        Привет{user?.first_name ? `, ${user.first_name}` : ""}!
      </h1>
      <p className="mt-2 text-text-muted">
        Добро пожаловать в ваше рабочее пространство
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <Link
          to="/kanban"
          className="rounded-xl border border-border bg-surface p-6 transition-shadow hover:shadow-md"
        >
          <h2 className="text-lg font-semibold text-primary">Kanban</h2>
          <p className="mt-2 text-sm text-text-muted">
            Управляйте заметками и задачами на досках
          </p>
        </Link>

        <Link
          to="/calendar"
          className="rounded-xl border border-border bg-surface p-6 transition-shadow hover:shadow-md"
        >
          <h2 className="text-lg font-semibold text-accent">Календарь</h2>
          <p className="mt-2 text-sm text-text-muted">
            Отслеживайте дни рождения близких
          </p>
        </Link>
      </div>
    </div>
  );
}
