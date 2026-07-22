import { useMemo } from "react";

import { createCrmApi } from "../api/crm";
import { useAuth } from "../context/AuthContext";

export function useCrmApi() {
  const { isAuthenticated } = useAuth();
  return useMemo(
    () => (isAuthenticated ? createCrmApi() : null),
    [isAuthenticated],
  );
}
