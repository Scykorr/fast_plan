import { useMemo } from "react";

import { createProcessApi } from "../api/process";
import { useAuth } from "../context/AuthContext";

export function useProcessApi() {
  const { isAuthenticated } = useAuth();
  return useMemo(
    () => (isAuthenticated ? createProcessApi() : null),
    [isAuthenticated],
  );
}
