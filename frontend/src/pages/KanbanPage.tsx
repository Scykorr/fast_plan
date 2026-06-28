import { useCallback, useEffect, useState } from "react";

import type { KanbanBoard } from "../api/kanban";
import { parseApiError } from "../api/errors";
import { ErrorMessage } from "../components/ErrorMessage";
import { KanbanBoardView } from "../components/kanban/KanbanBoardView";
import { useAuth } from "../context/AuthContext";
import { useKanbanApi } from "../hooks/useKanbanApi";

export function KanbanPage() {
  const { accessToken } = useAuth();
  const kanbanApi = useKanbanApi();
  const [board, setBoard] = useState<KanbanBoard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadBoard = useCallback(async () => {
    if (!kanbanApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const boards = await kanbanApi.getBoards();
      if (boards.length === 0) {
        setBoard(null);
        return;
      }
      const detail = await kanbanApi.getBoard(boards[0].id);
      setBoard(detail);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить доску"));
    } finally {
      setLoading(false);
    }
  }, [kanbanApi]);

  useEffect(() => {
    void loadBoard();
  }, [loadBoard]);

  if (loading) {
    return <p className="text-text-muted">Загрузка доски...</p>;
  }

  if (error) {
    return (
      <ErrorMessage message={error} onDismiss={() => void loadBoard()} />
    );
  }

  if (!board || !accessToken) {
    return <p className="text-text-muted">Доска не найдена</p>;
  }

  return (
    <KanbanBoardView
      board={board}
      token={accessToken}
      onBoardChange={setBoard}
    />
  );
}
