import { type FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

export function LoginPage() {
  const { login, complete2fa } = useAuth();
  const [searchParams] = useSearchParams();
  const next = searchParams.get("next");
  const registerHref = next
    ? `/register?next=${encodeURIComponent(next)}`
    : "/register";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [preAuthToken, setPreAuthToken] = useState("");
  const [error, setError] = useState("");
  const [needsVerification, setNeedsVerification] = useState(false);
  const [resendMessage, setResendMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [oauth, setOauth] = useState<{ microsoft: boolean }>({
    microsoft: false,
  });

  useEffect(() => {
    const oauthError = searchParams.get("oauth_error");
    if (oauthError) {
      setError(
        oauthError === "invalid_state"
          ? "Сессия OAuth истекла. Попробуйте снова."
          : `Ошибка входа через SSO (${oauthError}).`,
      );
    }
    const token = searchParams.get("pre_auth_token");
    if (searchParams.get("oauth_2fa") === "1" && token) {
      setPreAuthToken(token);
    }
  }, [searchParams]);

  useEffect(() => {
    void api
      .oauthProviders()
      .then((p) => setOauth({ microsoft: p.microsoft }))
      .catch(() => setOauth({ microsoft: false }));
  }, []);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setNeedsVerification(false);
    setResendMessage("");
    setLoading(true);
    try {
      if (preAuthToken) {
        await complete2fa(preAuthToken, totpCode);
        setPreAuthToken("");
        setTotpCode("");
        return;
      }
      const result = await login(email, password);
      if (result?.requires_2fa) {
        setPreAuthToken(result.pre_auth_token);
      }
    } catch (err) {
      const detail =
        err instanceof ApiError && typeof err.data.detail === "string"
          ? err.data.detail
          : "";
      if (detail.includes("Подтвердите email")) {
        setNeedsVerification(true);
        setError(detail);
        return;
      }
      setError(
        err instanceof ApiError
          ? preAuthToken
            ? "Неверный код 2FA"
            : "Неверный email или пароль"
          : "Не удалось войти. Попробуйте снова.",
      );
    } finally {
      setLoading(false);
    }
  };

  const showOauth = !preAuthToken && oauth.microsoft;

  return (
    <div className="flex min-h-screen items-center justify-center auth-hero px-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-text">Вход</h1>
        <p className="mt-2 text-sm text-text-muted">
          {preAuthToken
            ? "Введите код из приложения-аутентификатора"
            : "Добро пожаловать в Fast Plan"}
        </p>

        {showOauth && (
          <div className="mt-6 space-y-2">
            <a
              href={api.oauthStartUrl("microsoft", next)}
              className="flex w-full items-center justify-center rounded-lg border border-border bg-cream px-4 py-2.5 text-sm font-medium text-text transition-colors hover:bg-surface"
            >
              Войти через Microsoft
            </a>
            <p className="pt-1 text-center text-xs text-text-muted">или email</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          {!preAuthToken ? (
            <>
              <div>
                <label htmlFor="email" className="mb-1 block text-sm font-medium">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-border bg-cream px-3 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div>
                <label htmlFor="password" className="mb-1 block text-sm font-medium">
                  Пароль
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-border bg-cream px-3 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
                <p className="mt-1 text-right text-xs">
                  <Link to="/forgot-password" className="text-primary hover:underline">
                    Забыли пароль?
                  </Link>
                </p>
              </div>
            </>
          ) : (
            <div>
              <label htmlFor="totp" className="mb-1 block text-sm font-medium">
                Код 2FA
              </label>
              <input
                id="totp"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                required
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                className="w-full rounded-lg border border-border bg-cream px-3 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
              <button
                type="button"
                className="mt-2 text-xs text-primary hover:underline"
                onClick={() => {
                  setPreAuthToken("");
                  setTotpCode("");
                  setError("");
                }}
              >
                Назад к паролю
              </button>
            </div>
          )}

          {error && (
            <p className="text-sm text-primary" role="alert">
              {error}
            </p>
          )}

          {needsVerification && (
            <div className="rounded-lg border border-border bg-cream p-3 text-sm">
              <button
                type="button"
                className="font-medium text-primary hover:underline"
                onClick={async () => {
                  await api.resendVerification(email);
                  setResendMessage("Новая ссылка отправлена.");
                }}
              >
                Отправить ссылку повторно
              </button>
              {resendMessage && (
                <p className="mt-1 text-xs text-secondary" role="status">
                  {resendMessage}
                </p>
              )}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-primary-hover disabled:opacity-60"
          >
            {loading ? "Вход..." : preAuthToken ? "Подтвердить" : "Войти"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-text-muted">
          Нет аккаунта?{" "}
          <Link to={registerHref} className="font-medium text-primary hover:underline">
            Зарегистрироваться
          </Link>
        </p>
      </div>
    </div>
  );
}
