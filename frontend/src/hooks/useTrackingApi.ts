import { useMemo } from "react";

import { createTrackingApi } from "../api/tracking";
import { useAuth } from "../context/AuthContext";

export function useTrackingApi() {
  const { isAuthenticated } = useAuth();
  return useMemo(
    () => (isAuthenticated ? createTrackingApi() : null),
    [isAuthenticated],
  );
}
