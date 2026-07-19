import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { api, ApiError } from "../api/client";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.forgotPassword(email.trim());
      setDone(true);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? "Не удалось отправить письмо. Проверьте email."
          : "Не удалось отправить письмо. Попробуйте снова.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-cream px-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-text">Восстановление пароля</h1>
        <p className="mt-2 text-sm text-text-muted">
          Укажите email — мы отправим ссылку для сброса пароля.
        </p>

        {done ? (
          <div className="mt-8 space-y-4">
            <p className="rounded-lg bg-cream px-3 py-2 text-sm text-text" role="status">
              Если аккаунт с таким email существует, письмо со ссылкой уже отправлено.
            </p>
            <Link to="/login" className="block text-center text-sm font-medium text-primary hover:underline">
              Вернуться ко входу
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-8 space-y-4" noValidate>
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
              {loading ? "Отправка..." : "Отправить ссылку"}
            </button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-text-muted">
          <Link to="/login" className="font-medium text-primary hover:underline">
            Назад ко входу
          </Link>
        </p>
      </div>
    </div>
  );
}
