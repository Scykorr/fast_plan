import { type FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api, ApiError } from "../api/client";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const uid = searchParams.get("uid") ?? "";
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (!uid || !token) {
      setError("Ссылка сброса недействительна.");
      return;
    }
    if (password.length < 8) {
      setError("Пароль должен быть не короче 8 символов.");
      return;
    }
    if (password !== confirm) {
      setError("Пароли не совпадают.");
      return;
    }
    setLoading(true);
    try {
      await api.resetPassword({ uid, token, new_password: password });
      navigate("/login", { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? "Ссылка недействительна или истекла. Запросите новую."
          : "Не удалось сбросить пароль.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-cream px-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-text">Новый пароль</h1>
        <p className="mt-2 text-sm text-text-muted">Задайте новый пароль для входа.</p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4" noValidate>
          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium">
              Новый пароль
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
          </div>
          <div>
            <label htmlFor="confirm" className="mb-1 block text-sm font-medium">
              Повтор пароля
            </label>
            <input
              id="confirm"
              type="password"
              required
              minLength={8}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="w-full rounded-lg border border-border bg-cream px-3 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </div>

          {error && (
            <p className="text-sm text-primary" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-primary-hover disabled:opacity-60"
          >
            {loading ? "Сохранение..." : "Сохранить пароль"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-text-muted">
          <Link to="/forgot-password" className="font-medium text-primary hover:underline">
            Запросить новую ссылку
          </Link>
        </p>
      </div>
    </div>
  );
}
