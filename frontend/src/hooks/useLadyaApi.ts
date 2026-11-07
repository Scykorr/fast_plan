import { useMemo } from "react";

import { createLadyaApi } from "../api/ladya";
import { useAuth } from "../context/AuthContext";

export function useLadyaApi() {
  const { isAuthenticated } = useAuth();
  return useMemo(
    () => (isAuthenticated ? createLadyaApi() : null),
    [isAuthenticated],
  );
}
