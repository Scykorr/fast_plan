import { useMemo } from "react";

import { createWorkspaceApi } from "../api/workspace";
import { useAuth } from "../context/AuthContext";

export function useWorkspaceApi() {
  const { accessToken } = useAuth();
  return useMemo(
    () => (accessToken ? createWorkspaceApi(accessToken) : null),
    [accessToken],
  );
}
