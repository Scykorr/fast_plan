import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, setActiveWorkspaceId, type User } from "../api/client";

type AuthContextValue = {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    username: string;
    password: string;
    first_name?: string;
    last_name?: string;
  }) => Promise<void>;
  updateProfile: (formData: FormData) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // Ignore network/session errors on logout.
    }
    setUser(null);
    setActiveWorkspaceId(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await api.login({ email, password });
    if (result.user.active_workspace_id) {
      setActiveWorkspaceId(result.user.active_workspace_id);
    }
    setUser(result.user);
  }, []);

  const register = useCallback(
    async (data: {
      email: string;
      username: string;
      password: string;
      first_name?: string;
      last_name?: string;
    }) => {
      await api.register(data);
    },
    [],
  );

  const updateProfile = useCallback(async (formData: FormData) => {
    const updatedUser = await api.updateProfile(formData);
    setUser(updatedUser);
  }, []);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        await api.ensureCsrf();
        const me = await api.me();
        if (me.active_workspace_id) {
          setActiveWorkspaceId(me.active_workspace_id);
        }
        setUser(me);
      } catch {
        const refreshed = await api.refresh();
        if (!refreshed) {
          setUser(null);
          setIsLoading(false);
          return;
        }
        try {
          const me = await api.me();
          if (me.active_workspace_id) {
            setActiveWorkspaceId(me.active_workspace_id);
          }
          setUser(me);
        } catch {
          setUser(null);
        }
      } finally {
        setIsLoading(false);
      }
    };
    void bootstrap();
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      register,
      updateProfile,
      logout,
    }),
    [user, isLoading, login, register, updateProfile, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
