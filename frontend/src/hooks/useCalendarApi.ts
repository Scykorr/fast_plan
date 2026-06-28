import { useMemo } from "react";

import { createCalendarApi } from "../api/calendar";
import { useAuth } from "../context/AuthContext";

export function useCalendarApi() {
  const { accessToken } = useAuth();

  return useMemo(() => {
    if (!accessToken) {
      return null;
    }
    return createCalendarApi(accessToken);
  }, [accessToken]);
}
