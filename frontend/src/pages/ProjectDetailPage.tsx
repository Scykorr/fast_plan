import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { parseApiError } from "../api/errors";
import type { ProjectFinance } from "../api/finance";
import type { KanbanBoard } from "../api/kanban";
import type {
  CriticalPath,
  Project,
  ProjectBaseline,
  ProjectDashboard,
  ProjectSchedule,
  ProjectStatusReport,
  RACIEntry,
  Risk,
  Stakeholder,
  WBSNode,
  WorkItemComment,
} from "../api/projects";
import { ErrorMessage } from "../components/ErrorMessage";
import { CommentThread } from "../components/comments/CommentThread";
import type { WorkspaceMember } from "../api/workspace";
import { ProjectBudgetSummary } from "../components/finance/ProjectBudgetSummary";
import { KanbanBoardView } from "../components/kanban/KanbanBoardView";
import {
  collectKanbanAssignees,
  collectKanbanStatuses,
} from "../components/kanban/kanbanFilters";
import {
  BaselineView,
  CriticalPathView,
} from "../components/projects/BaselineView";
import { CharterEditor } from "../components/projects/CharterEditor";
import { GanttChart } from "../components/projects/GanttChart";
import { ProjectCalendar } from "../components/projects/ProjectCalendar";
import { RiskRegister } from "../components/projects/RiskRegister";
import { StakeholderPanel } from "../components/projects/StakeholderPanel";
import { StatusReportDigest } from "../components/projects/StatusReportDigest";
import { WorkItemDetailPanel } from "../components/tracking/WorkItemDetailPanel";
import { WBSTreeView } from "../components/projects/WBSTreeView";
import {
  collectWbsAssignees,
  collectWbsStatuses,
  filterWbsTree,
} from "../components/projects/wbs/filterWbs";
import { useAuth } from "../context/AuthContext";
import { useWorkspace } from "../context/WorkspaceContext";
import { useConfirm } from "../hooks/useConfirm";
import { useFinanceApi } from "../hooks/useFinanceApi";
import { useKanbanApi } from "../hooks/useKanbanApi";
import { useProjectsApi } from "../hooks/useProjectsApi";
import { useTrackingApi } from "../hooks/useTrackingApi";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";
import type { TrackingMetadata } from "../api/tracking";
import {
  mergeDeepLinkSearch,
  parseDeepLinkParams,
} from "../utils/deepLinks";
import { downloadBlob } from "../utils/download";

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

const TABS: Tab[] = [
  "overview",
  "wbs",
  "gantt",
  "kanban",
  "calendar",
  "risks",
  "stakeholders",
  "baseline",
  "analytics",
];

function flattenWBS(nodes: WBSNode[]): WBSNode[] {
  return nodes.flatMap((node) => [node, ...flattenWBS(node.children)]);
}

function isTab(value: string | null | undefined): value is Tab {
  return value != null && (TABS as string[]).includes(value);
}

export function ProjectDetailPage() {
  const { projectId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const deepLink = parseDeepLinkParams(searchParams);
  const { isAuthenticated, user } = useAuth();
  const { activeWorkspace, switchWorkspace, isLoading: workspaceLoading } =
    useWorkspace();
  const id = Number(projectId);
  const projectsApi = useProjectsApi();
  const financeApi = useFinanceApi();
  const kanbanApi = useKanbanApi();
  const trackingApi = useTrackingApi();
  const workspaceApi = useWorkspaceApi();
  const { confirm, dialog: confirmDialog } = useConfirm();

  const tab: Tab = isTab(deepLink.tab) ? deepLink.tab : "overview";
  const [project, setProject] = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<ProjectDashboard | null>(null);
  const [projectFinance, setProjectFinance] = useState<ProjectFinance | null>(null);
  const [statusReport, setStatusReport] = useState<ProjectStatusReport | null>(
    null,
  );
  const [wbs, setWbs] = useState<WBSNode[]>([]);
  const [schedule, setSchedule] = useState<ProjectSchedule | null>(null);
  const [board, setBoard] = useState<KanbanBoard | null>(null);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([]);
  const [raci, setRaci] = useState<RACIEntry[]>([]);
  const [baselines, setBaselines] = useState<ProjectBaseline[]>([]);
  const [criticalPath, setCriticalPath] = useState<CriticalPath | null>(null);
  const [selectedNode, setSelectedNode] = useState<WBSNode | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailMode, setDetailMode] = useState<"project" | "issue">("issue");
  const [nodeComments, setNodeComments] = useState<WorkItemComment[]>([]);
  const [trackingMetadata, setTrackingMetadata] = useState<TrackingMetadata | null>(null);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [workspaceReady, setWorkspaceReady] = useState(false);

  const patchSearch = useCallback(
    (updates: Parameters<typeof mergeDeepLinkSearch>[1]) => {
      setSearchParams(
        (current) => mergeDeepLinkSearch(current, updates),
        { replace: true },
      );
    },
    [setSearchParams],
  );

  useEffect(() => {
    if (workspaceLoading) {
      return;
    }
    const targetWorkspace = deepLink.workspace;
    if (
      targetWorkspace != null &&
      activeWorkspace &&
      activeWorkspace.id !== targetWorkspace
    ) {
      setWorkspaceReady(false);
      void switchWorkspace(targetWorkspace).then(() => setWorkspaceReady(true));
      return;
    }
    setWorkspaceReady(true);
  }, [
    workspaceLoading,
    deepLink.workspace,
    activeWorkspace,
    switchWorkspace,
  ]);

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
        exportData,
        financeData,
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
        projectsApi.exportProject(id),
        financeApi ? financeApi.getProjectFinance(id) : Promise.resolve(null),
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
      setStatusReport(exportData);
      setProjectFinance(financeData);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить проект"));
    } finally {
      setLoading(false);
    }
  }, [projectsApi, financeApi, id]);

  useEffect(() => {
    if (!workspaceReady) {
      return;
    }
    void loadAll();
  }, [loadAll, workspaceReady]);

  useEffect(() => {
    if (!trackingApi) {
      return;
    }
    void trackingApi.getMetadata().then(setTrackingMetadata).catch(() => undefined);
  }, [trackingApi]);

  useEffect(() => {
    if (!workspaceApi) {
      return;
    }
    void workspaceApi.getMembers().then(setMembers).catch(() => undefined);
  }, [workspaceApi]);

  useEffect(() => {
    if (!deepLink.node || wbs.length === 0) {
      return;
    }
    const node = flattenWBS(wbs).find((item) => item.id === deepLink.node);
    if (!node) {
      return;
    }
    setSelectedNode(node);
    setDetailMode(node.parent_id === null ? "project" : "issue");
    setDetailOpen(true);
    if (tab !== "wbs" && !deepLink.card) {
      patchSearch({ tab: "wbs" });
    }
  }, [deepLink.node, deepLink.card, wbs, tab, patchSearch]);

  useEffect(() => {
    if (deepLink.risk == null) {
      return;
    }
    if (tab !== "risks") {
      patchSearch({ tab: "risks" });
      return;
    }
    const el = document.getElementById(`risk-${deepLink.risk}`);
    el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [deepLink.risk, tab, patchSearch, risks]);

  useEffect(() => {
    if (deepLink.card == null) {
      return;
    }
    if (tab !== "kanban") {
      patchSearch({ tab: "kanban" });
    }
  }, [deepLink.card, tab, patchSearch]);

  useEffect(() => {
    if (!projectsApi || !selectedNode || detailMode !== "issue" || !detailOpen) {
      setNodeComments([]);
      return;
    }
    let cancelled = false;
    void projectsApi
      .getWbsComments(selectedNode.id)
      .then((items) => {
        if (!cancelled) {
          setNodeComments(items);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setNodeComments([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [projectsApi, selectedNode, detailMode, detailOpen]);

  const handleSelectWBSNode = (node: WBSNode) => {
    setSelectedNode(node);
    if (node.parent_id === null) {
      setDetailMode("project");
    } else {
      setDetailMode("issue");
    }
    setDetailOpen(true);
    patchSearch({ node: node.id, tab: "wbs" });
  };

  const handleCloseDetail = () => {
    setDetailOpen(false);
    patchSearch({ node: null });
  };

  const filteredWbs = useMemo(
    () =>
      filterWbsTree(wbs, {
        assigneeId: deepLink.assignee,
        statusId: deepLink.status,
      }),
    [wbs, deepLink.assignee, deepLink.status],
  );

  const wbsAssignees = useMemo(() => collectWbsAssignees(wbs), [wbs]);
  const wbsStatuses = useMemo(() => collectWbsStatuses(wbs), [wbs]);
  const kanbanAssignees = useMemo(
    () => (board ? collectKanbanAssignees(board) : []),
    [board],
  );
  const kanbanStatuses = useMemo(
    () => (board ? collectKanbanStatuses(board) : []),
    [board],
  );

  const handleSaveProjectDetail = async (body: {
    name?: string;
    description?: string;
    tracker_id?: number | null;
    workflow_status_id?: number | null;
    custom_values?: Record<string, string>;
  }) => {
    if (!projectsApi || !project) {
      return;
    }
    try {
      const updated = await projectsApi.patchProject(id, body);
      setProject(updated);
      await loadAll();
      setDetailOpen(false);
    } catch (err) {
      setError(parseApiError(err, "Не удалось сохранить проект"));
    }
  };

  const handleSaveNodeDetail = async (
    nodeId: number,
    body: {
      title?: string;
      description?: string;
      tracker_id?: number | null;
      workflow_status_id?: number | null;
      assignee_id?: number | null;
      custom_values?: Record<string, string>;
    },
  ) => {
    if (!projectsApi) {
      return;
    }
    try {
      const tree = await projectsApi.updateWBSNode(nodeId, body);
      setWbs(tree);
      const updated = flattenWBS(tree).find((item) => item.id === nodeId) ?? null;
      setSelectedNode(updated);
      await loadAll();
      setDetailOpen(false);
    } catch (err) {
      setError(parseApiError(err, "Не удалось сохранить задачу"));
    }
  };

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

  const handleAddWBS = async (parentId: number, title: string) => {
    if (!projectsApi) {
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
    if (!projectsApi || !(await confirm("Удалить узел WBS?"))) {
      return;
    }
    try {
      await projectsApi.deleteWBSNode(nodeId);
      if (selectedNode?.id === nodeId) {
        setSelectedNode(null);
      }
      await loadAll();
    } catch (err) {
      setError(parseApiError(err, "Не удалось удалить узел"));
    }
  };

  const handleRenameWBS = async (nodeId: number, title: string) => {
    if (!projectsApi) {
      return;
    }
    try {
      const tree = await projectsApi.updateWBSNode(nodeId, { title });
      setWbs(tree);
      await loadAll();
    } catch (err) {
      setError(parseApiError(err, "Не удалось переименовать узел"));
    }
  };

  const handleMoveWBS = async (nodeId: number, parentId: number, position: number) => {
    if (!projectsApi) {
      return;
    }
    try {
      const tree = await projectsApi.updateWBSNode(nodeId, { parent_id: parentId, position });
      setWbs(tree);
      const moved = flattenWBS(tree).find((node) => node.id === nodeId) ?? null;
      if (moved) {
        setSelectedNode(moved);
      }
      await loadAll();
    } catch (err) {
      setError(parseApiError(err, "Не удалось переместить узел"));
    }
  };

  const handleAddRisk = async (values: {
    title: string;
    probability: number;
    impact: number;
  }) => {
    if (!projectsApi) {
      return;
    }
    try {
      await projectsApi.createRisk(id, values);
      setRisks(await projectsApi.getRisks(id));
      setDashboard(await projectsApi.getDashboard(id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать риск"));
      throw err;
    }
  };

  const handleUpdateRisk = async (
    riskId: number,
    values: {
      title: string;
      description: string;
      status: string;
      mitigation: string;
      probability: number;
      impact: number;
    },
  ) => {
    if (!projectsApi) {
      return;
    }
    try {
      await projectsApi.updateRisk(riskId, values);
      setRisks(await projectsApi.getRisks(id));
      setDashboard(await projectsApi.getDashboard(id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось обновить риск"));
      throw err;
    }
  };

  const handleAddStakeholder = async (values: { name: string; role: string }) => {
    if (!projectsApi) {
      return;
    }
    try {
      await projectsApi.createStakeholder(id, {
        name: values.name,
        role: values.role,
      });
      setStakeholders(await projectsApi.getStakeholders(id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить стейкхолдера"));
      throw err;
    }
  };

  const handleUpdateStakeholder = async (
    stakeholderId: number,
    values: {
      name: string;
      role: string;
      interest: number;
      influence: number;
      contact_email: string;
      notes: string;
    },
  ) => {
    if (!projectsApi) {
      return;
    }
    try {
      await projectsApi.updateStakeholder(stakeholderId, values);
      setStakeholders(await projectsApi.getStakeholders(id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось обновить стейкхолдера"));
      throw err;
    }
  };

  const handleUpdateBaseline = async (baselineId: number, name: string) => {
    if (!projectsApi) {
      return;
    }
    try {
      await projectsApi.updateBaseline(baselineId, name);
      setBaselines(await projectsApi.getBaselines(id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось переименовать baseline"));
      throw err;
    }
  };

  const handleDeleteBaseline = async (baselineId: number) => {
    if (!projectsApi || !(await confirm("Удалить baseline?"))) {
      return;
    }
    try {
      await projectsApi.deleteBaseline(baselineId);
      setBaselines(await projectsApi.getBaselines(id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось удалить baseline"));
    }
  };

  const handleAddRACI = async (values: {
    wbs_node_id: number;
    stakeholder_id: number;
    raci_type: "R" | "A" | "C" | "I";
  }) => {
    if (!projectsApi) {
      return;
    }
    try {
      await projectsApi.createRACI(id, values);
      setRaci(await projectsApi.getRACI(id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать RACI"));
      throw err;
    }
  };

  const handleExport = async () => {
    if (!projectsApi) {
      return;
    }
    try {
      const data = statusReport ?? (await projectsApi.exportProject(id));
      setStatusReport(data);
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

  const handleExportPdf = async () => {
    if (!projectsApi) {
      return;
    }
    try {
      const blob = await projectsApi.exportProjectPdf(id);
      downloadBlob(blob, `project-${id}-status.pdf`);
    } catch (err) {
      setError(parseApiError(err, "Не удалось экспортировать PDF"));
    }
  };

  const handleExportWbs = async (format: "csv" | "xlsx") => {
    if (!projectsApi) {
      return;
    }
    try {
      const blob = await projectsApi.exportWbs(id, format);
      downloadBlob(blob, `project-${id}-wbs.${format}`);
    } catch (err) {
      setError(parseApiError(err, "Не удалось экспортировать WBS"));
    }
  };

  const handleDownloadMilestonesIcs = async () => {
    if (!projectsApi) {
      return;
    }
    try {
      const blob = await projectsApi.downloadProjectMilestonesIcs(id);
      downloadBlob(blob, `project-${id}-milestones.ics`);
    } catch (err) {
      setError(parseApiError(err, "Не удалось скачать календарь вех"));
    }
  };

  const handleAddComment = async (
    body: string,
    kind: "comment" | "decision",
  ) => {
    if (!projectsApi || !selectedNode) {
      return;
    }
    try {
      await projectsApi.createWbsComment(selectedNode.id, { body, kind });
      setNodeComments(await projectsApi.getWbsComments(selectedNode.id));
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить комментарий"));
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    if (!projectsApi) {
      return;
    }
    try {
      await projectsApi.deleteComment(commentId);
      if (selectedNode) {
        setNodeComments(await projectsApi.getWbsComments(selectedNode.id));
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось удалить комментарий"));
    }
  };

  if (loading || !workspaceReady) {
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
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}

      <div className="flex flex-wrap gap-1 border-b border-border">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => patchSearch({ tab: item.id })}
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

      {tab === "overview" && (
        <div className="space-y-4">
          {statusReport && (
            <StatusReportDigest
              report={statusReport}
              onExportJson={() => void handleExport()}
              onExportPdf={() => void handleExportPdf()}
            />
          )}

          <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-surface p-4">
            <span className="text-sm font-medium text-text-muted">Экспорт WBS:</span>
            <button
              type="button"
              onClick={() => void handleExportWbs("csv")}
              className="rounded-lg border border-border bg-cream px-3 py-1.5 text-sm font-medium text-text hover:bg-border/30"
            >
              CSV
            </button>
            <button
              type="button"
              onClick={() => void handleExportWbs("xlsx")}
              className="rounded-lg border border-border bg-cream px-3 py-1.5 text-sm font-medium text-text hover:bg-border/30"
            >
              XLSX
            </button>
            <button
              type="button"
              onClick={() => void handleDownloadMilestonesIcs()}
              className="rounded-lg border border-border bg-cream px-3 py-1.5 text-sm font-medium text-text hover:bg-border/30"
            >
              Вехи в календарь (.ics)
            </button>
          </div>

          {dashboard && (
            <>
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

              {projectFinance && (
                <ProjectBudgetSummary
                  finance={projectFinance}
                  title="Budget vs actual"
                />
              )}

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
            </>
          )}
        </div>
      )}

      {tab === "wbs" && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-text-muted">
              Исполнитель
              <select
                className="rounded-lg border border-border bg-surface px-2 py-1.5 text-text"
                value={deepLink.assignee ?? ""}
                onChange={(event) => {
                  const value = event.target.value;
                  patchSearch({
                    assignee: value ? Number(value) : null,
                    tab: "wbs",
                  });
                }}
              >
                <option value="">Все</option>
                {wbsAssignees.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm text-text-muted">
              Статус
              <select
                className="rounded-lg border border-border bg-surface px-2 py-1.5 text-text"
                value={deepLink.status ?? ""}
                onChange={(event) => {
                  const value = event.target.value;
                  patchSearch({
                    status: value ? Number(value) : null,
                    tab: "wbs",
                  });
                }}
              >
                <option value="">Все</option>
                {wbsStatuses.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <WBSTreeView
            nodes={filteredWbs}
            onAddChild={(parentId, title) => void handleAddWBS(parentId, title)}
            onAddSibling={(parentId, title) => void handleAddWBS(parentId, title)}
            onDelete={(nodeId) => void handleDeleteWBS(nodeId)}
            onRename={(nodeId, title) => void handleRenameWBS(nodeId, title)}
            onMove={(nodeId, parentId, position) =>
              void handleMoveWBS(nodeId, parentId, position)
            }
            selectedId={selectedNode?.id}
            onSelect={handleSelectWBSNode}
          />
        </div>
      )}

      {detailOpen && project && trackingMetadata && (
        <div className="space-y-4">
          <WorkItemDetailPanel
            mode={detailMode}
            project={project}
            node={detailMode === "project" ? null : selectedNode}
            metadata={trackingMetadata}
            onClose={handleCloseDetail}
            onSaveProject={(body) => void handleSaveProjectDetail(body)}
            onSaveNode={(nodeId, body) => void handleSaveNodeDetail(nodeId, body)}
          />
          {detailMode === "issue" && selectedNode && (
            <CommentThread
              comments={nodeComments}
              members={members}
              onAdd={(body, kind) => handleAddComment(body, kind)}
              onDelete={(commentId) => handleDeleteComment(commentId)}
              canDelete={Boolean(user)}
            />
          )}
        </div>
      )}

      {tab === "gantt" && schedule && (
        <GanttChart
          activities={schedule.activities}
          dependencies={schedule.dependencies}
        />
      )}

      {tab === "kanban" && board && isAuthenticated && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-text-muted">
              Исполнитель
              <select
                className="rounded-lg border border-border bg-surface px-2 py-1.5 text-text"
                value={deepLink.assignee ?? ""}
                onChange={(event) => {
                  const value = event.target.value;
                  patchSearch({
                    assignee: value ? Number(value) : null,
                    tab: "kanban",
                  });
                }}
              >
                <option value="">Все</option>
                {kanbanAssignees.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm text-text-muted">
              Статус
              <select
                className="rounded-lg border border-border bg-surface px-2 py-1.5 text-text"
                value={deepLink.status ?? ""}
                onChange={(event) => {
                  const value = event.target.value;
                  patchSearch({
                    status: value ? Number(value) : null,
                    tab: "kanban",
                  });
                }}
              >
                <option value="">Все</option>
                {kanbanStatuses.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <KanbanBoardView
            board={board}
            onBoardChange={(updated) => void handleBoardChange(updated)}
            selectedCardId={deepLink.card}
            filter={{
              assigneeId: deepLink.assignee,
              statusId: deepLink.status,
            }}
            onSelectCard={(cardId) =>
              patchSearch({ card: cardId, tab: "kanban" })
            }
          />
        </div>
      )}

      {tab === "kanban" && !board && (
        <p className="text-sm text-text-muted">Kanban-доска проекта не найдена</p>
      )}

      {tab === "calendar" && isAuthenticated && (
        <ProjectCalendar projectId={project.id} />
      )}

      {tab === "risks" && (
        <RiskRegister
          risks={risks}
          highlightedRiskId={deepLink.risk}
          onAdd={(values) => handleAddRisk(values)}
          onUpdate={(riskId, values) => handleUpdateRisk(riskId, values)}
          onDelete={async (riskId) => {
            if (!projectsApi || !(await confirm("Удалить риск?"))) {
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
          onAddStakeholder={(values) => handleAddStakeholder(values)}
          onUpdateStakeholder={(stakeholderId, values) =>
            handleUpdateStakeholder(stakeholderId, values)
          }
          onDeleteStakeholder={async (stakeholderId) => {
            if (!projectsApi || !(await confirm("Удалить стейкхолдера?"))) {
              return;
            }
            await projectsApi.deleteStakeholder(stakeholderId);
            setStakeholders(await projectsApi.getStakeholders(id));
          }}
          onAddRACI={(values) => handleAddRACI(values)}
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
          onCreate={async (name) => {
            if (!projectsApi) {
              return;
            }
            try {
              await projectsApi.createBaseline(id, name);
              setBaselines(await projectsApi.getBaselines(id));
            } catch (err) {
              setError(parseApiError(err, "Не удалось создать baseline"));
              throw err;
            }
          }}
          onRename={(baselineId, name) => handleUpdateBaseline(baselineId, name)}
          onDelete={(baselineId) => handleDeleteBaseline(baselineId)}
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
      {confirmDialog}
    </div>
  );
}
