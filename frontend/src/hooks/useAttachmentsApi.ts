import { useMemo } from "react";

import { createAttachmentsApi } from "../api/attachments";
import { useAuth } from "../context/AuthContext";

export function useAttachmentsApi() {
  const { isAuthenticated } = useAuth();
  return useMemo(
    () => (isAuthenticated ? createAttachmentsApi() : null),
    [isAuthenticated],
  );
}
