import { useMemo } from "react";

import { createNotificationsApi } from "../api/notifications";
import { useAuth } from "../context/AuthContext";

export function useNotificationsApi() {
  const { isAuthenticated } = useAuth();
  return useMemo(
    () => (isAuthenticated ? createNotificationsApi() : null),
    [isAuthenticated],
  );
}
