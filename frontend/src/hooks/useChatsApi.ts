import { useMemo } from "react";

import { createChatsApi } from "../api/chats";
import { useAuth } from "../context/AuthContext";

export function useChatsApi() {
  const { isAuthenticated } = useAuth();

  return useMemo(() => {
    if (!isAuthenticated) {
      return null;
    }
    return createChatsApi();
  }, [isAuthenticated]);
}
