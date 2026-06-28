import { useMemo } from "react";

import { createKanbanApi } from "../api/kanban";
import { useAuth } from "../context/AuthContext";

export function useKanbanApi() {
  const { accessToken } = useAuth();

  return useMemo(() => {
    if (!accessToken) {
      return null;
    }
    return createKanbanApi(accessToken);
  }, [accessToken]);
}
