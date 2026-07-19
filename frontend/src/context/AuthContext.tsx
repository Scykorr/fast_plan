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

const ACCESS_KEY = "fast_plan_access";
const REFRESH_KEY = "fast_plan_refresh";

type AuthContextValue = {
  user: User | null;
  accessToken: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    username: string;
    password: string;
    first_name?: string;
    last_name?: string;
  }) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(
    () => localStorage.getItem(ACCESS_KEY),
  );
  const [isLoading, setIsLoading] = useState(true);

  const persistTokens = (access: string, refresh: string) => {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
    setAccessToken(access);
  };

  const logout = useCallback(() => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setAccessToken(null);
    setUser(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await api.login({ email, password });
    persistTokens(tokens.access, tokens.refresh);
    const me = await api.me(tokens.access);
    if (me.active_workspace_id) {
      setActiveWorkspaceId(me.active_workspace_id);
    }
    setUser(me);
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
      await login(data.email, data.password);
    },
    [login],
  );

  useEffect(() => {
    const bootstrap = async () => {
      if (!accessToken) {
        setIsLoading(false);
        return;
      }
      try {
        const me = await api.me(accessToken);
        setUser(me);
      } catch {
        const refresh = localStorage.getItem(REFRESH_KEY);
        if (!refresh) {
          logout();
          setIsLoading(false);
          return;
        }
        try {
          const { access } = await api.refresh(refresh);
          persistTokens(access, refresh);
          const me = await api.me(access);
          setUser(me);
        } catch {
          logout();
        }
      } finally {
        setIsLoading(false);
      }
    };
    void bootstrap();
  }, [accessToken, logout]);

  const value = useMemo(
    () => ({ user, accessToken, isLoading, login, register, logout }),
    [user, accessToken, isLoading, login, register, logout],
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
