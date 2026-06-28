import { Link } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../api/errors";
import type { Project } from "../api/projects";
import { ErrorMessage } from "../components/ErrorMessage";
import { useProjectsApi } from "../hooks/useProjectsApi";

const statusLabels: Record<string, string> = {
  planning: "Планирование",
  active: "Активный",
  on_hold: "На паузе",
  completed: "Завершён",
  cancelled: "Отменён",
};

export function ProjectsPage() {
  const projectsApi = useProjectsApi();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadProjects = useCallback(async () => {
    if (!projectsApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await projectsApi.getProjects();
      setProjects(data);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить проекты"));
    } finally {
      setLoading(false);
    }
  }, [projectsApi]);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  const handleCreate = async () => {
    if (!projectsApi) {
      return;
    }
    const name = window.prompt("Название проекта");
    if (!name?.trim()) {
      return;
    }
    try {
      await projectsApi.createProject({ name: name.trim(), status: "planning" });
      await loadProjects();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать проект"));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text">Проекты</h1>
          <p className="mt-1 text-sm text-text-muted">
            Управление по PMBOK: WBS, Gantt, Kanban
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleCreate()}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover"
        >
          + Новый проект
        </button>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      {loading ? (
        <p className="text-text-muted">Загрузка...</p>
      ) : projects.length === 0 ? (
        <p className="text-text-muted">Проектов пока нет</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {projects.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="rounded-xl border border-border bg-surface p-6 transition-shadow hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-2">
                <h2 className="text-lg font-semibold text-text">{project.name}</h2>
                <span className="rounded-full bg-accent/15 px-2 py-0.5 text-xs text-accent">
                  {statusLabels[project.status] ?? project.status}
                </span>
              </div>
              {project.description && (
                <p className="mt-2 line-clamp-2 text-sm text-text-muted">
                  {project.description}
                </p>
              )}
              <div className="mt-4 flex items-center gap-4 text-xs text-text-muted">
                <span>WBS: {project.wbs_count}</span>
                <span>Прогресс: {project.progress}%</span>
              </div>
              <div className="mt-3 h-2 rounded-full bg-cream">
                <div
                  className="h-2 rounded-full bg-secondary transition-all"
                  style={{ width: `${project.progress}%` }}
                />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
