import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { parseApiError } from "../api/errors";
import type {
  Project,
  ProjectDashboard,
  ProjectSchedule,
  WBSNode,
} from "../api/projects";
import { ErrorMessage } from "../components/ErrorMessage";
import { GanttChart } from "../components/projects/GanttChart";
import { WBSTreeView } from "../components/projects/WBSTreeView";
import { useProjectsApi } from "../hooks/useProjectsApi";

type Tab = "overview" | "wbs" | "gantt";

export function ProjectDetailPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const projectsApi = useProjectsApi();

  const [tab, setTab] = useState<Tab>("overview");
  const [project, setProject] = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<ProjectDashboard | null>(null);
  const [wbs, setWbs] = useState<WBSNode[]>([]);
  const [schedule, setSchedule] = useState<ProjectSchedule | null>(null);
  const [selectedNode, setSelectedNode] = useState<WBSNode | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadAll = useCallback(async () => {
    if (!projectsApi || !id) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [projectData, dashboardData, wbsData, scheduleData] = await Promise.all([
        projectsApi.getProject(id),
        projectsApi.getDashboard(id),
        projectsApi.getWBS(id),
        projectsApi.getSchedule(id),
      ]);
      setProject(projectData);
      setDashboard(dashboardData);
      setWbs(wbsData);
      setSchedule(scheduleData);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить проект"));
    } finally {
      setLoading(false);
    }
  }, [projectsApi, id]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const handleAddWBS = async (parentId: number) => {
    if (!projectsApi) {
      return;
    }
    const title = window.prompt("Название work package");
    if (!title?.trim()) {
      return;
    }
    try {
      const tree = await projectsApi.createWBSNode(id, {
        title: title.trim(),
        parent_id: parentId,
        node_type: "work_package",
      });
      setWbs(tree);
      const scheduleData = await projectsApi.getSchedule(id);
      setSchedule(scheduleData);
      await loadAll();
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить узел WBS"));
    }
  };

  const handleDeleteWBS = async (nodeId: number) => {
    if (!projectsApi || !window.confirm("Удалить узел WBS?")) {
      return;
    }
    try {
      await projectsApi.deleteWBSNode(nodeId);
      await loadAll();
    } catch (err) {
      setError(parseApiError(err, "Не удалось удалить узел"));
    }
  };

  if (loading) {
    return <p className="text-text-muted">Загрузка проекта...</p>;
  }

  if (!project) {
    return <p className="text-primary">Проект не найден</p>;
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Обзор" },
    { id: "wbs", label: "WBS" },
    { id: "gantt", label: "Gantt" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <Link to="/projects" className="text-sm text-text-muted hover:text-primary">
          ← Все проекты
        </Link>
        <h1 className="mt-2 text-3xl font-bold text-text">{project.name}</h1>
        <p className="mt-1 text-sm text-text-muted">{project.description}</p>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      <div className="flex flex-wrap gap-2 border-b border-border">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={[
              "border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              tab === item.id
                ? "border-primary text-primary"
                : "border-transparent text-text-muted hover:text-text",
            ].join(" ")}
          >
            {item.label}
          </button>
        ))}
        <Link
          to={`/kanban?project=${project.id}`}
          className="ml-auto self-center text-sm text-secondary hover:underline"
        >
          Kanban доска →
        </Link>
      </div>

      {tab === "overview" && dashboard && (
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-border bg-surface p-5">
            <p className="text-sm text-text-muted">Прогресс</p>
            <p className="mt-1 text-3xl font-bold text-secondary">
              {dashboard.progress}%
            </p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-5">
            <p className="text-sm text-text-muted">Узлов WBS</p>
            <p className="mt-1 text-3xl font-bold text-text">{dashboard.wbs_count}</p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-5">
            <p className="text-sm text-text-muted">Статус</p>
            <p className="mt-1 text-lg font-semibold text-primary">{dashboard.status}</p>
          </div>
        </div>
      )}

      {tab === "wbs" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-border bg-surface p-4">
            <h2 className="mb-4 text-lg font-semibold text-text">Иерархия работ</h2>
            <WBSTreeView
              nodes={wbs}
              onAddChild={(parentId) => void handleAddWBS(parentId)}
              onDelete={(nodeId) => void handleDeleteWBS(nodeId)}
              selectedId={selectedNode?.id}
              onSelect={setSelectedNode}
            />
          </div>
          <div className="rounded-xl border border-border bg-surface p-4">
            <h2 className="mb-4 text-lg font-semibold text-text">Детали узла</h2>
            {selectedNode ? (
              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-text-muted">Код</dt>
                  <dd className="font-mono font-medium">{selectedNode.code}</dd>
                </div>
                <div>
                  <dt className="text-text-muted">Название</dt>
                  <dd className="font-medium">{selectedNode.title}</dd>
                </div>
                <div>
                  <dt className="text-text-muted">Тип</dt>
                  <dd>{selectedNode.node_type}</dd>
                </div>
                {selectedNode.schedule && (
                  <>
                    <div>
                      <dt className="text-text-muted">Период</dt>
                      <dd>
                        {selectedNode.schedule.start_date} — {selectedNode.schedule.end_date}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-text-muted">Прогресс</dt>
                      <dd>{selectedNode.schedule.progress}%</dd>
                    </div>
                  </>
                )}
                {selectedNode.card_id && (
                  <div>
                    <dt className="text-text-muted">Kanban</dt>
                    <dd>
                      <Link
                        to={`/kanban?project=${project.id}`}
                        className="text-primary hover:underline"
                      >
                        Карточка #{selectedNode.card_id}
                      </Link>
                    </dd>
                  </div>
                )}
              </dl>
            ) : (
              <p className="text-sm text-text-muted">Выберите узел в дереве</p>
            )}
          </div>
        </div>
      )}

      {tab === "gantt" && schedule && (
        <GanttChart
          activities={schedule.activities}
          dependencies={schedule.dependencies}
        />
      )}
    </div>
  );
}
