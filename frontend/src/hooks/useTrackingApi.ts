import { useMemo } from "react";

import { createTrackingApi } from "../api/tracking";
import { useAuth } from "../context/AuthContext";

export function useTrackingApi() {
  const { accessToken } = useAuth();
  return useMemo(
    () => (accessToken ? createTrackingApi(accessToken) : null),
    [accessToken],
  );
}
