import { useMemo } from "react";

import { createFinanceApi } from "../api/finance";
import { useAuth } from "../context/AuthContext";

export function useFinanceApi() {
  const { accessToken } = useAuth();
  return useMemo(
    () => (accessToken ? createFinanceApi(accessToken) : null),
    [accessToken],
  );
}
