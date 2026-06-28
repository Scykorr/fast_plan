import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { parseApiError } from "../api/errors";
import type { KanbanBoard } from "../api/kanban";
import type {
  CriticalPath,
  Project,
  ProjectBaseline,
  ProjectDashboard,
  ProjectSchedule,
  RACIEntry,
  Risk,
  Stakeholder,
  WBSNode,
} from "../api/projects";
import { ErrorMessage } from "../components/ErrorMessage";
import { KanbanBoardView } from "../components/kanban/KanbanBoardView";
import {
  BaselineView,
  CriticalPathView,
} from "../components/projects/BaselineView";
import { CharterEditor } from "../components/projects/CharterEditor";
import { GanttChart } from "../components/projects/GanttChart";
import { ProjectCalendar } from "../components/projects/ProjectCalendar";
import { RiskRegister } from "../components/projects/RiskRegister";
import { StakeholderPanel } from "../components/projects/StakeholderPanel";
import { WBSTreeView } from "../components/projects/WBSTreeView";
import { useAuth } from "../context/AuthContext";
import { useKanbanApi } from "../hooks/useKanbanApi";
import { useProjectsApi } from "../hooks/useProjectsApi";

type Tab =
  | "overview"
  | "wbs"
  | "gantt"
  | "kanban"
  | "calendar"
  | "risks"
  | "stakeholders"
  | "baseline"
  | "analytics";

function flattenWBS(nodes: WBSNode[]): WBSNode[] {
  return nodes.flatMap((node) => [node, ...flattenWBS(node.children)]);
}

export function ProjectDetailPage() {
  const { projectId } = useParams();
  const { accessToken } = useAuth();
  const id = Number(projectId);
  const projectsApi = useProjectsApi();
  const kanbanApi = useKanbanApi();

  const [tab, setTab] = useState<Tab>("overview");
  const [project, setProject] = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<ProjectDashboard | null>(null);
  const [wbs, setWbs] = useState<WBSNode[]>([]);
  const [schedule, setSchedule] = useState<ProjectSchedule | null>(null);
  const [board, setBoard] = useState<KanbanBoard | null>(null);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([]);
  const [raci, setRaci] = useState<RACIEntry[]>([]);
  const [baselines, setBaselines] = useState<ProjectBaseline[]>([]);
  const [criticalPath, setCriticalPath] = useState<CriticalPath | null>(null);
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
      const [
        projectData,
        dashboardData,
        wbsData,
        scheduleData,
        risksData,
        stakeholdersData,
        raciData,
        baselinesData,
        cpmData,
      ] = await Promise.all([
        projectsApi.getProject(id),
        projectsApi.getDashboard(id),
        projectsApi.getWBS(id),
        projectsApi.getSchedule(id),
        projectsApi.getRisks(id),
        projectsApi.getStakeholders(id),
        projectsApi.getRACI(id),
        projectsApi.getBaselines(id),
        projectsApi.getCriticalPath(id),
      ]);
      setProject(projectData);
      setDashboard(dashboardData);
      setWbs(wbsData);
      setSchedule(scheduleData);
      setRisks(risksData);
      setStakeholders(stakeholdersData);
      setRaci(raciData);
      setBaselines(baselinesData);
      setCriticalPath(cpmData);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить проект"));
    } finally {
      setLoading(false);
    }
  }, [projectsApi, id]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const loadBoard = useCallback(async () => {
    if (!kanbanApi || !project?.board_id) {
      return;
    }
    try {
      setBoard(await kanbanApi.getBoard(project.board_id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить Kanban-доску"));
    }
  }, [kanbanApi, project?.board_id]);

  useEffect(() => {
    if (tab === "kanban") {
      void loadBoard();
    }
  }, [tab, loadBoard]);

  const handleBoardChange = async (updated: KanbanBoard) => {
    setBoard(updated);
    if (!projectsApi) {
      return;
    }
    const [wbsData, scheduleData, dashboardData] = await Promise.all([
      projectsApi.getWBS(id),
      projectsApi.getSchedule(id),
      projectsApi.getDashboard(id),
    ]);
    setWbs(wbsData);
    setSchedule(scheduleData);
    setDashboard(dashboardData);
  };

  const handleAddWBS = async (parentId: number) => {
    if (!projectsApi) {
      return;
    }
    const title = window.prompt("Название work package");
    if (!title?.trim()) {
      return;
    }
    try {
      await projectsApi.createWBSNode(id, {
        title: title.trim(),
        parent_id: parentId,
        node_type: "work_package",
      });
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

  const handleAddRisk = async () => {
    if (!projectsApi) {
      return;
    }
    const title = window.prompt("Название риска");
    if (!title?.trim()) {
      return;
    }
    try {
      await projectsApi.createRisk(id, { title: title.trim(), probability: 3, impact: 3 });
      setRisks(await projectsApi.getRisks(id));
      setDashboard(await projectsApi.getDashboard(id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать риск"));
    }
  };

  const handleAddStakeholder = async () => {
    if (!projectsApi) {
      return;
    }
    const name = window.prompt("Имя стейкхолдера");
    if (!name?.trim()) {
      return;
    }
    try {
      await projectsApi.createStakeholder(id, { name: name.trim(), role: "" });
      setStakeholders(await projectsApi.getStakeholders(id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить стейкхолдера"));
    }
  };

  const handleAddRACI = async () => {
    if (!projectsApi) {
      return;
    }
    const nodes = flattenWBS(wbs);
    const node = nodes[1] ?? nodes[0];
    const stakeholder = stakeholders[0];
    if (!node || !stakeholder) {
      return;
    }
    const raciType = window.prompt("RACI (R/A/C/I)", "R");
    if (!raciType) {
      return;
    }
    try {
      await projectsApi.createRACI(id, {
        wbs_node_id: node.id,
        stakeholder_id: stakeholder.id,
        raci_type: raciType.toUpperCase(),
      });
      setRaci(await projectsApi.getRACI(id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать RACI"));
    }
  };

  const handleExport = async () => {
    if (!projectsApi) {
      return;
    }
    try {
      const data = await projectsApi.exportProject(id);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `project-${id}-status.json`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(parseApiError(err, "Не удалось экспортировать отчёт"));
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
    { id: "kanban", label: "Kanban" },
    { id: "calendar", label: "Календарь" },
    { id: "risks", label: "Риски" },
    { id: "stakeholders", label: "Стейкхолдеры" },
    { id: "baseline", label: "Baseline" },
    { id: "analytics", label: "CPM / EVM" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/projects" className="text-sm text-text-muted hover:text-primary">
            ← Все проекты
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-text">{project.name}</h1>
          <p className="mt-1 text-sm text-text-muted">{project.description}</p>
        </div>
        <button
          type="button"
          onClick={() => void handleExport()}
          className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-text hover:bg-cream"
        >
          Экспорт JSON
        </button>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      <div className="flex flex-wrap gap-1 border-b border-border">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={[
              "border-b-2 px-3 py-2 text-sm font-medium transition-colors",
              tab === item.id
                ? "border-primary text-primary"
                : "border-transparent text-text-muted hover:text-text",
            ].join(" ")}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === "overview" && dashboard && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-4">
            <div className="rounded-xl border border-border bg-surface p-5">
              <p className="text-sm text-text-muted">Прогресс</p>
              <p className="mt-1 text-3xl font-bold text-secondary">
                {dashboard.progress}%
              </p>
            </div>
            <div className="rounded-xl border border-border bg-surface p-5">
              <p className="text-sm text-text-muted">Бюджет</p>
              <p className="mt-1 text-2xl font-bold text-text">
                {dashboard.budget.toLocaleString("ru-RU")} ₽
              </p>
            </div>
            <div className="rounded-xl border border-border bg-surface p-5">
              <p className="text-sm text-text-muted">Крит. путь</p>
              <p className="mt-1 text-2xl font-bold text-primary">
                {dashboard.critical_path.critical_count} задач
              </p>
            </div>
            <div className="rounded-xl border border-border bg-surface p-5">
              <p className="text-sm text-text-muted">SPI / CPI</p>
              <p className="mt-1 text-lg font-semibold text-text">
                {dashboard.evm.spi ?? "—"} / {dashboard.evm.cpi ?? "—"}
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-surface p-5">
            <h2 className="mb-4 text-lg font-semibold text-text">Устав проекта</h2>
            <CharterEditor
              charter={dashboard.charter}
              onSave={async (data) => {
                if (!projectsApi) {
                  return;
                }
                const updated = await projectsApi.patchCharter(id, data);
                setDashboard((current) =>
                  current ? { ...current, charter: updated } : current,
                );
              }}
            />
          </div>

          {dashboard.top_risks.length > 0 && (
            <div className="rounded-xl border border-border bg-surface p-5">
              <h2 className="mb-3 text-lg font-semibold text-text">Топ-риски</h2>
              <ul className="space-y-2 text-sm">
                {dashboard.top_risks.map((risk) => (
                  <li key={risk.id} className="flex justify-between">
                    <span>{risk.title}</span>
                    <span className="font-medium text-primary">{risk.score}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {dashboard.upcoming_milestones.length > 0 && (
            <div className="rounded-xl border border-border bg-surface p-5">
              <h2 className="mb-3 text-lg font-semibold text-text">Ближайшие вехи</h2>
              <ul className="space-y-2 text-sm">
                {dashboard.upcoming_milestones.map((milestone) => (
                  <li key={milestone.id} className="flex justify-between gap-4">
                    <span>
                      {milestone.code} {milestone.name}
                    </span>
                    <span className="text-text-muted">{milestone.start_date}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
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
                {selectedNode.schedule && (
                  <div>
                    <dt className="text-text-muted">Прогресс</dt>
                    <dd>{selectedNode.schedule.progress}%</dd>
                  </div>
                )}
                {selectedNode.card_id && (
                  <div>
                    <dt className="text-text-muted">Kanban</dt>
                    <dd>
                      <button
                        type="button"
                        onClick={() => setTab("kanban")}
                        className="text-primary hover:underline"
                      >
                        Карточка #{selectedNode.card_id}
                      </button>
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

      {tab === "kanban" && board && accessToken && (
        <KanbanBoardView
          board={board}
          token={accessToken}
          onBoardChange={(updated) => void handleBoardChange(updated)}
        />
      )}

      {tab === "kanban" && !board && (
        <p className="text-sm text-text-muted">Kanban-доска проекта не найдена</p>
      )}

      {tab === "calendar" && accessToken && (
        <ProjectCalendar projectId={project.id} token={accessToken} />
      )}

      {tab === "risks" && (
        <RiskRegister
          risks={risks}
          onAdd={() => void handleAddRisk()}
          onDelete={async (riskId) => {
            if (!projectsApi) {
              return;
            }
            await projectsApi.deleteRisk(riskId);
            setRisks(await projectsApi.getRisks(id));
          }}
        />
      )}

      {tab === "stakeholders" && (
        <StakeholderPanel
          stakeholders={stakeholders}
          raci={raci}
          wbs={wbs}
          onAddStakeholder={() => void handleAddStakeholder()}
          onDeleteStakeholder={async (stakeholderId) => {
            if (!projectsApi) {
              return;
            }
            await projectsApi.deleteStakeholder(stakeholderId);
            setStakeholders(await projectsApi.getStakeholders(id));
          }}
          onAddRACI={() => void handleAddRACI()}
          onDeleteRACI={async (entryId) => {
            if (!projectsApi) {
              return;
            }
            await projectsApi.deleteRACI(entryId);
            setRaci(await projectsApi.getRACI(id));
          }}
        />
      )}

      {tab === "baseline" && (
        <BaselineView
          baselines={baselines}
          schedule={schedule}
          onCreate={async () => {
            if (!projectsApi) {
              return;
            }
            const name = window.prompt("Название baseline") ?? undefined;
            await projectsApi.createBaseline(id, name);
            setBaselines(await projectsApi.getBaselines(id));
          }}
        />
      )}

      {tab === "analytics" && (
        <div className="space-y-6">
          {dashboard && (
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-xl border border-border bg-surface p-4">
                <p className="text-sm text-text-muted">Earned Value</p>
                <p className="text-xl font-bold">{dashboard.evm.earned_value} ₽</p>
              </div>
              <div className="rounded-xl border border-border bg-surface p-4">
                <p className="text-sm text-text-muted">Planned Value</p>
                <p className="text-xl font-bold">{dashboard.evm.planned_value} ₽</p>
              </div>
              <div className="rounded-xl border border-border bg-surface p-4">
                <p className="text-sm text-text-muted">Actual Cost</p>
                <p className="text-xl font-bold">{dashboard.evm.actual_cost} ₽</p>
              </div>
            </div>
          )}
          <CriticalPathView data={criticalPath} />
        </div>
      )}
    </div>
  );
}
