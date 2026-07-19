import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  getActiveWorkspaceId,
  setActiveWorkspaceId,
} from "../api/client";
import {
  createWorkspaceApi,
  type WorkspaceSummary,
} from "../api/workspace";
import { useAuth } from "./AuthContext";

type WorkspaceContextValue = {
  workspaces: WorkspaceSummary[];
  activeWorkspace: WorkspaceSummary | null;
  isLoading: boolean;
  refreshWorkspaces: () => Promise<void>;
  switchWorkspace: (workspaceId: number) => Promise<void>;
  workspaceEpoch: number;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, user } = useAuth();
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [workspaceEpoch, setWorkspaceEpoch] = useState(0);

  const refreshWorkspaces = useCallback(async () => {
    if (!isAuthenticated) {
      setWorkspaces([]);
      return;
    }
    setIsLoading(true);
    try {
      const api = createWorkspaceApi();
      const items = await api.listWorkspaces();
      setWorkspaces(items);
      const preferred =
        items.find((item) => item.is_active) ??
        items.find((item) => item.id === (user?.active_workspace_id ?? getActiveWorkspaceId())) ??
        items[0] ??
        null;
      if (preferred) {
        setActiveWorkspaceId(preferred.id);
      }
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, user?.active_workspace_id]);

  const switchWorkspace = useCallback(
    async (workspaceId: number) => {
      if (!isAuthenticated) {
        return;
      }
      const api = createWorkspaceApi();
      setActiveWorkspaceId(workspaceId);
      const activated = await api.activateWorkspace(workspaceId);
      setWorkspaces((prev) =>
        prev.map((item) => ({
          ...item,
          is_active: item.id === activated.id,
        })),
      );
      setWorkspaceEpoch((value) => value + 1);
    },
    [isAuthenticated],
  );

  useEffect(() => {
    if (!isAuthenticated) {
      setWorkspaces([]);
      return;
    }
    if (user?.active_workspace_id) {
      setActiveWorkspaceId(user.active_workspace_id);
    }
    void refreshWorkspaces();
  }, [isAuthenticated, user?.active_workspace_id, refreshWorkspaces]);

  const activeWorkspace = useMemo(() => {
    const activeId = getActiveWorkspaceId();
    return (
      workspaces.find((item) => item.is_active) ??
      workspaces.find((item) => item.id === activeId) ??
      null
    );
  }, [workspaces, workspaceEpoch]);

  const value = useMemo(
    () => ({
      workspaces,
      activeWorkspace,
      isLoading,
      refreshWorkspaces,
      switchWorkspace,
      workspaceEpoch,
    }),
    [
      workspaces,
      activeWorkspace,
      isLoading,
      refreshWorkspaces,
      switchWorkspace,
      workspaceEpoch,
    ],
  );

  return (
    <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used within WorkspaceProvider");
  }
  return context;
}
