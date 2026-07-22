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
  login: (
    email: string,
    password: string,
  ) => Promise<{ requires_2fa: true; pre_auth_token: string } | void>;
  complete2fa: (preAuthToken: string, code: string) => Promise<void>;
  register: (data: {
    email: string;
    username: string;
    password: string;
    first_name?: string;
    last_name?: string;
  }) => Promise<void>;
  updateProfile: (formData: FormData) => Promise<void>;
  setUser: (user: User | null) => void;
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

  const applyUser = useCallback((next: User) => {
    if (next.active_workspace_id) {
      setActiveWorkspaceId(next.active_workspace_id);
    }
    setUser(next);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await api.login({ email, password });
      if ("requires_2fa" in result && result.requires_2fa) {
        return {
          requires_2fa: true as const,
          pre_auth_token: result.pre_auth_token,
        };
      }
      if (!("user" in result) || !result.user) {
        throw new Error("Unexpected login response");
      }
      applyUser(result.user);
    },
    [applyUser],
  );

  const complete2fa = useCallback(
    async (preAuthToken: string, code: string) => {
      const result = await api.verify2fa({
        pre_auth_token: preAuthToken,
        code,
      });
      applyUser(result.user);
    },
    [applyUser],
  );

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
      complete2fa,
      register,
      updateProfile,
      setUser,
      logout,
    }),
    [user, isLoading, login, complete2fa, register, updateProfile, logout],
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
