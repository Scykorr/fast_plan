import { Link } from "react-router-dom";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { parseApiError } from "../api/errors";
import type { Project, ProjectTemplate } from "../api/projects";
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
  const [templates, setTemplates] = useState<ProjectTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("planning");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [templateId, setTemplateId] = useState<number | "">("");
  const [templateName, setTemplateName] = useState("");
  const [templateSourceId, setTemplateSourceId] = useState<number | "">("");

  const loadProjects = useCallback(async () => {
    if (!projectsApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [projectData, templateData] = await Promise.all([
        projectsApi.getProjects(),
        projectsApi.getProjectTemplates(),
      ]);
      setProjects(projectData);
      setTemplates(templateData);
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
    setTemplateId("");
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
        template_id: templateId || undefined,
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
            <label htmlFor="project-template" className="mb-1 block text-sm font-medium">
              Шаблон
            </label>
            <select
              id="project-template"
              value={templateId}
              onChange={(event) =>
                setTemplateId(event.target.value ? Number(event.target.value) : "")
              }
              className={inputClass}
            >
              <option value="">Без шаблона</option>
              {templates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name}
                </option>
              ))}
            </select>
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

      {projects.length > 0 && (
        <section className="max-w-2xl rounded-xl border border-border bg-surface p-4">
          <h2 className="font-semibold text-text">Шаблоны проектов</h2>
          <p className="mt-1 text-xs text-text-muted">
            Сохраните WBS, выбранные трекеры и колонки Kanban существующего проекта.
          </p>
          <form
            className="mt-3 flex flex-wrap gap-2"
            onSubmit={async (event) => {
              event.preventDefault();
              if (!projectsApi || !templateName.trim() || !templateSourceId) return;
              try {
                await projectsApi.createProjectTemplate({
                  name: templateName.trim(),
                  source_project_id: templateSourceId,
                });
                setTemplateName("");
                setTemplateSourceId("");
                await loadProjects();
              } catch (err) {
                setError(parseApiError(err, "Не удалось создать шаблон"));
              }
            }}
          >
            <input
              required
              placeholder="Название шаблона"
              value={templateName}
              onChange={(event) => setTemplateName(event.target.value)}
              className={`${inputClass} min-w-48 flex-1`}
            />
            <select
              required
              value={templateSourceId}
              onChange={(event) =>
                setTemplateSourceId(event.target.value ? Number(event.target.value) : "")
              }
              className={`${inputClass} min-w-48 flex-1`}
            >
              <option value="">Исходный проект</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
            <button
              type="submit"
              className="rounded-lg bg-secondary px-3 py-2 text-sm font-semibold text-white"
            >
              Сохранить
            </button>
          </form>
          {templates.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-2">
              {templates.map((template) => (
                <li
                  key={template.id}
                  className="rounded-full border border-border bg-cream px-3 py-1 text-xs text-text"
                >
                  {template.name}
                </li>
              ))}
            </ul>
          )}
        </section>
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
