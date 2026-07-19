import { useMemo } from "react";

import { createCalendarApi } from "../api/calendar";
import { useAuth } from "../context/AuthContext";

export function useCalendarApi() {
  const { isAuthenticated } = useAuth();

  return useMemo(() => {
    if (!isAuthenticated) {
      return null;
    }
    return createCalendarApi();
  }, [isAuthenticated]);
}
