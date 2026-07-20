import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { parseApiError } from "../api/errors";
import { setActiveWorkspaceId } from "../api/client";
import { ErrorMessage } from "../components/ErrorMessage";
import { useAuth } from "../context/AuthContext";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

export function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { user, isLoading: authLoading } = useAuth();
  const workspaceApi = useWorkspaceApi();
  const [error, setError] = useState("");
  const [status, setStatus] = useState<"idle" | "accepting" | "done">("idle");

  useEffect(() => {
    if (authLoading || !user || !workspaceApi || !token || status !== "idle") {
      return;
    }
    setStatus("accepting");
    void workspaceApi
      .acceptInvitation(token)
      .then(async (result) => {
        setActiveWorkspaceId(result.workspace_id);
        setStatus("done");
        navigate("/", { replace: true });
      })
      .catch((err) => {
        setError(parseApiError(err, "Не удалось принять приглашение"));
        setStatus("idle");
      });
  }, [authLoading, user, workspaceApi, token, status, navigate]);

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center auth-hero">
        <p className="text-text-muted">Загрузка...</p>
      </div>
    );
  }

  if (!user) {
    const next = `/invite/${token ?? ""}`;
    return (
      <div className="flex min-h-screen items-center justify-center auth-hero px-4">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-text">Приглашение в workspace</h1>
          <p className="mt-3 text-sm text-text-muted">
            Войдите или зарегистрируйтесь с email, на который отправлено
            приглашение, чтобы присоединиться.
          </p>
          <div className="mt-6 flex flex-col gap-3">
            <Link
              to={`/login?next=${encodeURIComponent(next)}`}
              className="rounded-lg bg-primary px-4 py-2.5 text-center text-sm font-semibold text-white hover:bg-primary-hover"
            >
              Войти
            </Link>
            <Link
              to={`/register?next=${encodeURIComponent(next)}`}
              className="rounded-lg border border-border px-4 py-2.5 text-center text-sm font-semibold text-text hover:bg-cream"
            >
              Зарегистрироваться
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center auth-hero px-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-text">Принятие приглашения</h1>
        {error && (
          <div className="mt-4">
            <ErrorMessage message={error} onDismiss={() => setError("")} />
          </div>
        )}
        {!error && (
          <p className="mt-3 text-sm text-text-muted">
            {status === "accepting" || status === "done"
              ? "Присоединяем вас к workspace..."
              : "Подготовка..."}
          </p>
        )}
        {error && (
          <Link to="/" className="mt-4 inline-block text-sm text-primary hover:underline">
            На дашборд
          </Link>
        )}
      </div>
    </div>
  );
}
