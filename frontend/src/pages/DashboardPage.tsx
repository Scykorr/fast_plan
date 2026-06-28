import { Link } from "react-router-dom";
import { useEffect, useState } from "react";

import type { UpcomingBirthday } from "../api/calendar";
import { parseApiError } from "../api/errors";
import { ErrorMessage } from "../components/ErrorMessage";
import { UpcomingBirthdays } from "../components/calendar/UpcomingBirthdays";
import { useAuth } from "../context/AuthContext";
import { useCalendarApi } from "../hooks/useCalendarApi";

export function DashboardPage() {
  const { user } = useAuth();
  const calendarApi = useCalendarApi();
  const [upcoming, setUpcoming] = useState<UpcomingBirthday[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      if (!calendarApi) {
        return;
      }
      setLoading(true);
      try {
        const data = await calendarApi.getUpcoming(5);
        setUpcoming(data);
      } catch (err) {
        setError(parseApiError(err, "Не удалось загрузить дни рождения"));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [calendarApi]);

  return (
    <div>
      <h1 className="text-3xl font-bold text-text">
        Привет{user?.first_name ? `, ${user.first_name}` : ""}!
      </h1>
      <p className="mt-2 text-text-muted">
        Добро пожаловать в ваше рабочее пространство
      </p>

      <section className="mt-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text">Ближайшие дни рождения</h2>
          <Link to="/calendar" className="text-sm font-medium text-accent hover:underline">
            Календарь →
          </Link>
        </div>
        <ErrorMessage message={error} onDismiss={() => setError("")} />
        <UpcomingBirthdays items={upcoming} loading={loading} />
      </section>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Link
          to="/projects"
          className="rounded-xl border border-border bg-surface p-6 transition-shadow hover:shadow-md"
        >
          <h2 className="text-lg font-semibold text-primary">Проекты</h2>
          <p className="mt-2 text-sm text-text-muted">
            WBS, Gantt и Kanban по PMBOK
          </p>
        </Link>

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
