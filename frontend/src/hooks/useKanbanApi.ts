import { useMemo } from "react";

import { createKanbanApi } from "../api/kanban";
import { useAuth } from "../context/AuthContext";

export function useKanbanApi() {
  const { isAuthenticated } = useAuth();

  return useMemo(() => {
    if (!isAuthenticated) {
      return null;
    }
    return createKanbanApi();
  }, [isAuthenticated]);
}
