import { useMemo } from "react";

import { createProjectsApi } from "../api/projects";
import { useAuth } from "../context/AuthContext";

export function useProjectsApi() {
  const { isAuthenticated } = useAuth();

  return useMemo(() => {
    if (!isAuthenticated) {
      return null;
    }
    return createProjectsApi();
  }, [isAuthenticated]);
}
