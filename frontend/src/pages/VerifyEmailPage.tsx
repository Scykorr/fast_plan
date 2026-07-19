import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api/client";

type VerificationState = "loading" | "success" | "error";

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const [state, setState] = useState<VerificationState>("loading");

  useEffect(() => {
    const uid = searchParams.get("uid");
    const token = searchParams.get("token");
    if (!uid || !token) {
      setState("error");
      return;
    }
    api
      .verifyEmail({ uid, token })
      .then(() => setState("success"))
      .catch(() => setState("error"));
  }, [searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-cream px-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 text-center shadow-sm">
        {state === "loading" && (
          <>
            <h1 className="text-2xl font-bold text-text">Подтверждаем email</h1>
            <p className="mt-3 text-sm text-text-muted">Подождите немного…</p>
          </>
        )}
        {state === "success" && (
          <>
            <h1 className="text-2xl font-bold text-text">Email подтверждён</h1>
            <p className="mt-3 text-sm text-text-muted">
              Теперь вы можете войти в Fast Plan.
            </p>
            <Link
              to="/login"
              className="mt-6 inline-block rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover"
            >
              Войти
            </Link>
          </>
        )}
        {state === "error" && (
          <>
            <h1 className="text-2xl font-bold text-text">Ссылка не работает</h1>
            <p className="mt-3 text-sm text-text-muted">
              Ссылка недействительна или устарела. Запросите новую на странице входа.
            </p>
            <Link
              to="/login"
              className="mt-6 inline-block font-medium text-primary hover:underline"
            >
              Перейти ко входу
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
