import { type FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { parseApiError } from "../api/errors";
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
  const [emailSent, setEmailSent] = useState<boolean | null>(null);
  const [verifyRequired, setVerifyRequired] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await register({
        email,
        username,
        password,
        first_name: firstName,
        last_name: lastName,
      });
      setVerifyRequired(Boolean(result.email_verification_required));
      setEmailSent(
        result.email_verification_required ? Boolean(result.email_sent) : null,
      );
      setRegistered(true);
    } catch (err) {
      setError(
        parseApiError(err, "Не удалось зарегистрироваться. Проверьте данные."),
      );
    } finally {
      setLoading(false);
    }
  };

  if (registered) {
    let statusText =
      "Аккаунт создан. Можно сразу войти — подтверждение email сейчас не требуется.";
    if (verifyRequired && emailSent) {
      statusText = `Письмо со ссылкой подтверждения отправлено на ${email}. Проверьте Входящие и Спам.`;
    } else if (verifyRequired && emailSent === false) {
      statusText = `Аккаунт создан, но письмо на ${email} не удалось отправить (SMTP). На экране входа нажмите «Отправить письмо ещё раз» или попросите администратора проверить почту.`;
    }
    return (
      <div className="flex min-h-screen items-center justify-center auth-hero px-4">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 text-center shadow-sm">
          <h1 className="text-2xl font-bold text-text">Аккаунт создан</h1>
          <p className="mt-3 text-sm text-text-muted">{statusText}</p>
          <div className="mt-6 flex justify-center gap-3">
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
    <div className="flex min-h-screen items-center justify-center auth-hero px-4">
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
              pattern="[\w.@+-]+"
              title="Буквы, цифры и символы @ . + - _ без пробелов"
              placeholder="tony_fedos"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-border bg-cream px-3 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
            <p className="mt-1 text-xs text-text-muted">
              Без пробелов: буквы, цифры, @ . + - _
            </p>
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
