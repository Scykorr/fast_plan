import { useMemo } from "react";

import { createWorkspaceApi } from "../api/workspace";
import { useAuth } from "../context/AuthContext";

export function useWorkspaceApi() {
  const { isAuthenticated } = useAuth();
  return useMemo(
    () => (isAuthenticated ? createWorkspaceApi() : null),
    [isAuthenticated],
  );
}
