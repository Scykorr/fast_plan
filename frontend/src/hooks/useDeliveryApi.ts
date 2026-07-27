import { useMemo } from "react";

import { createDeliveryApi } from "../api/delivery";
import { useAuth } from "../context/AuthContext";

export function useDeliveryApi() {
  const { isAuthenticated } = useAuth();
  return useMemo(
    () => (isAuthenticated ? createDeliveryApi() : null),
    [isAuthenticated],
  );
}
