import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import type { BoardFlowAnalytics, KanbanBoard } from "../api/kanban";
import { parseApiError } from "../api/errors";
import { ErrorMessage } from "../components/ErrorMessage";
import { KanbanBoardView } from "../components/kanban/KanbanBoardView";
import { FlowAnalytics } from "../components/kanban/FlowAnalytics";
import {
  collectKanbanAssignees,
  collectKanbanStatuses,
} from "../components/kanban/kanbanFilters";
import { useAuth } from "../context/AuthContext";
import { useWorkspace } from "../context/WorkspaceContext";
import { useKanbanApi } from "../hooks/useKanbanApi";
import { useProjectsApi } from "../hooks/useProjectsApi";
import {
  mergeDeepLinkSearch,
  parseDeepLinkParams,
} from "../utils/deepLinks";

export function KanbanPage() {
  const { isAuthenticated } = useAuth();
  const { activeWorkspace, switchWorkspace, isLoading: workspaceLoading } =
    useWorkspace();
  const kanbanApi = useKanbanApi();
  const projectsApi = useProjectsApi();
  const [searchParams, setSearchParams] = useSearchParams();
  const deepLink = parseDeepLinkParams(searchParams);
  const projectId = deepLink.project;

  const [board, setBoard] = useState<KanbanBoard | null>(null);
  const [boardTitle, setBoardTitle] = useState("");
  const [analytics, setAnalytics] = useState<BoardFlowAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
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

  const loadBoard = useCallback(async () => {
    if (!kanbanApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      if (projectId && projectsApi) {
        const project = await projectsApi.getProject(projectId);
        if (project.board_id) {
          const detail = await kanbanApi.getBoard(project.board_id);
          setBoard(detail);
          setAnalytics(await kanbanApi.getBoardAnalytics(detail.id));
          setBoardTitle(project.name);
          return;
        }
      }
      const boards = await kanbanApi.getBoards();
      if (boards.length === 0) {
        setBoard(null);
        return;
      }
      const detail = await kanbanApi.getBoard(boards[0].id);
      setBoard(detail);
      setAnalytics(await kanbanApi.getBoardAnalytics(detail.id));
      setBoardTitle(detail.title);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить доску"));
    } finally {
      setLoading(false);
    }
  }, [kanbanApi, projectsApi, projectId]);

  useEffect(() => {
    if (!workspaceReady) {
      return;
    }
    void loadBoard();
  }, [loadBoard, workspaceReady]);

  const assignees = useMemo(
    () => (board ? collectKanbanAssignees(board) : []),
    [board],
  );
  const statuses = useMemo(
    () => (board ? collectKanbanStatuses(board) : []),
    [board],
  );

  if (loading || !workspaceReady) {
    return <p className="text-text-muted">Загрузка доски...</p>;
  }

  if (error) {
    return (
      <ErrorMessage message={error} onDismiss={() => void loadBoard()} />
    );
  }

  if (!board || !isAuthenticated) {
    return <p className="text-text-muted">Доска не найдена</p>;
  }

  return (
    <div>
      {boardTitle && projectId != null && (
        <p className="mb-4 text-sm text-text-muted">
          Проектная доска: <span className="font-medium text-text">{boardTitle}</span>
        </p>
      )}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-text-muted">
          Исполнитель
          <select
            className="rounded-lg border border-border bg-surface px-2 py-1.5 text-text"
            value={deepLink.assignee ?? ""}
            onChange={(event) => {
              const value = event.target.value;
              patchSearch({ assignee: value ? Number(value) : null });
            }}
          >
            <option value="">Все</option>
            {assignees.map((option) => (
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
              patchSearch({ status: value ? Number(value) : null });
            }}
          >
            <option value="">Все</option>
            {statuses.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <KanbanBoardView
        board={board}
        
        onBoardChange={(updatedBoard) => {
          setBoard(updatedBoard);
          void kanbanApi
            ?.getBoardAnalytics(updatedBoard.id)
            .then(setAnalytics);
        }}
        selectedCardId={deepLink.card}
        filter={{
          assigneeId: deepLink.assignee,
          statusId: deepLink.status,
        }}
        onSelectCard={(cardId) => patchSearch({ card: cardId })}
      />
      {analytics && <FlowAnalytics data={analytics} />}
    </div>
  );
}
