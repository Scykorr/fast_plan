import { useMemo } from "react";

import { createProjectsApi } from "../api/projects";
import { useAuth } from "../context/AuthContext";

export function useProjectsApi() {
  const { accessToken } = useAuth();

  return useMemo(() => {
    if (!accessToken) {
      return null;
    }
    return createProjectsApi(accessToken);
  }, [accessToken]);
}
