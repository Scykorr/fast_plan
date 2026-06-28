import { useMemo } from "react";

import { createNotificationsApi } from "../api/notifications";
import { useAuth } from "../context/AuthContext";

export function useNotificationsApi() {
  const { accessToken } = useAuth();
  return useMemo(
    () => (accessToken ? createNotificationsApi(accessToken) : null),
    [accessToken],
  );
}
