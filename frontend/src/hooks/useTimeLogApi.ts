import { useMemo } from "react";

import { createTimeLogApi } from "../api/timelog";
import { useAuth } from "../context/AuthContext";

export function useTimeLogApi() {
  const { isAuthenticated } = useAuth();
  return useMemo(
    () => (isAuthenticated ? createTimeLogApi() : null),
    [isAuthenticated],
  );
}
