import { Link } from "react-router-dom";
import { useCallback, useEffect, useState, type FormEvent } from "react";

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

const inputClass =
  "w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20";

export function ProjectsPage() {
  const projectsApi = useProjectsApi();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("planning");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

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

  const resetForm = () => {
    setName("");
    setDescription("");
    setStatus("planning");
    setFormError("");
    setShowForm(false);
  };

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!projectsApi) {
      return;
    }
    if (!name.trim()) {
      setFormError("Укажите название проекта");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      await projectsApi.createProject({
        name: name.trim(),
        description: description.trim() || undefined,
        status,
      });
      resetForm();
      await loadProjects();
    } catch (err) {
      setFormError(parseApiError(err, "Не удалось создать проект"));
    } finally {
      setSaving(false);
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
          onClick={() => setShowForm((value) => !value)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover"
        >
          {showForm ? "Скрыть" : "+ Новый проект"}
        </button>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      {showForm && (
        <form
          onSubmit={handleCreate}
          noValidate
          className="max-w-lg space-y-3 rounded-xl border border-dashed border-border bg-surface p-4"
        >
          <div>
            <label htmlFor="project-name" className="mb-1 block text-sm font-medium">
              Название
            </label>
            <input
              id="project-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputClass}
              autoFocus
            />
          </div>
          <div>
            <label htmlFor="project-description" className="mb-1 block text-sm font-medium">
              Описание
            </label>
            <textarea
              id="project-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="project-status" className="mb-1 block text-sm font-medium">
              Статус
            </label>
            <select
              id="project-status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className={inputClass}
            >
              {Object.entries(statusLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          {formError && (
            <p className="text-sm text-primary" role="alert">
              {formError}
            </p>
          )}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
            >
              {saving ? "Создание..." : "Создать"}
            </button>
            <button
              type="button"
              onClick={resetForm}
              className="rounded-lg border border-border px-3 py-1.5 text-sm text-text-muted hover:bg-cream"
            >
              Отмена
            </button>
          </div>
        </form>
      )}

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
