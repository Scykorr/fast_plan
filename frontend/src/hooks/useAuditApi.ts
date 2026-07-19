import { useMemo } from "react";

import { createAuditApi } from "../api/audit";
import { useAuth } from "../context/AuthContext";

export function useAuditApi() {
  const { isAuthenticated } = useAuth();
  return useMemo(
    () => (isAuthenticated ? createAuditApi() : null),
    [isAuthenticated],
  );
}
