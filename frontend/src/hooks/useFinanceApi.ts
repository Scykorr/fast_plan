import { useMemo } from "react";

import { createFinanceApi } from "../api/finance";
import { useAuth } from "../context/AuthContext";

export function useFinanceApi() {
  const { isAuthenticated } = useAuth();
  return useMemo(
    () => (isAuthenticated ? createFinanceApi() : null),
    [isAuthenticated],
  );
}
