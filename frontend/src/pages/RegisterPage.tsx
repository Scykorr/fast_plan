import { type FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

export function RegisterPage() {
  const { register } = useAuth();
  const [searchParams] = useSearchParams();
  const next = searchParams.get("next");
  const loginHref = next ? `/login?next=${encodeURIComponent(next)}` : "/login";
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [registered, setRegistered] = useState(false);
  const [resendMessage, setResendMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register({
        email,
        username,
        password,
        first_name: firstName,
        last_name: lastName,
      });
      setRegistered(true);
    } catch (err) {
      if (err instanceof ApiError && err.data.email) {
        setError("Пользователь с таким email уже существует");
      } else {
        setError("Не удалось зарегистрироваться. Проверьте данные.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (registered) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cream px-4">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 text-center shadow-sm">
          <h1 className="text-2xl font-bold text-text">Проверьте почту</h1>
          <p className="mt-3 text-sm text-text-muted">
            Мы отправили ссылку подтверждения на <strong>{email}</strong>.
            Подтвердите адрес, затем войдите.
          </p>
          {resendMessage && (
            <p className="mt-3 text-sm text-secondary" role="status">
              {resendMessage}
            </p>
          )}
          <div className="mt-6 flex justify-center gap-3">
            <button
              type="button"
              className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-text hover:bg-cream"
              onClick={async () => {
                await api.resendVerification(email);
                setResendMessage("Новая ссылка отправлена.");
              }}
            >
              Отправить снова
            </button>
            <Link
              to={loginHref}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover"
            >
              Перейти ко входу
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-cream px-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-text">Регистрация</h1>
        <p className="mt-2 text-sm text-text-muted">
          Создайте аккаунт для начала работы
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
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

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="first-name" className="mb-1 block text-sm font-medium">
                Имя
              </label>
              <input
                id="first-name"
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="w-full rounded-lg border border-border bg-cream px-3 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div>
              <label htmlFor="last-name" className="mb-1 block text-sm font-medium">
                Фамилия
              </label>
              <input
                id="last-name"
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="w-full rounded-lg border border-border bg-cream px-3 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>

          <div>
            <label htmlFor="username" className="mb-1 block text-sm font-medium">
              Имя пользователя
            </label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
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
            {loading ? "Создание..." : "Создать аккаунт"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-text-muted">
          Уже есть аккаунт?{" "}
          <Link to={loginHref} className="font-medium text-primary hover:underline">
            Войти
          </Link>
        </p>
      </div>
    </div>
  );
}
