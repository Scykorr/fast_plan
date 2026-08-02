import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  approvePublicCrmDocument,
  fetchPublicCrmDocumentShare,
  publicCrmDocumentPdfUrl,
  type PublicCrmDocumentShare,
} from "../api/crm";
import { ErrorMessage } from "../components/ErrorMessage";

export function CommerceGuestPage() {
  const { token } = useParams<{ token: string }>();
  const [payload, setPayload] = useState<PublicCrmDocumentShare | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) {
      setError("Ссылка недействительна");
      setLoading(false);
      return;
    }
    void fetchPublicCrmDocumentShare(token)
      .then(setPayload)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  const approve = async () => {
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      const next = await approvePublicCrmDocument(token);
      setPayload(next);
      setMessage("Документ принят");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось принять");
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cream">
        <p className="text-text-muted">Загрузка документа…</p>
      </div>
    );
  }

  if (error || !payload) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cream px-4">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-text">Коммерческий документ</h1>
          <div className="mt-4">
            <ErrorMessage message={error || "Ссылка не найдена или истекла"} />
          </div>
          <Link
            to="/login"
            className="mt-4 inline-block text-sm text-primary hover:underline"
          >
            Войти в Fast Plan
          </Link>
        </div>
      </div>
    );
  }

  const doc = payload.document;
  const paymentLabel =
    doc.payment_status === "paid"
      ? "Оплачено полностью"
      : doc.payment_status === "partial"
        ? "Частичная оплата"
        : "Не оплачено";

  return (
    <div className="min-h-screen bg-cream px-4 py-8">
      <div className="mx-auto max-w-3xl space-y-6">
        <header className="rounded-2xl border border-border bg-surface p-6 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
            {payload.share.workspace_name}
          </p>
          <h1 className="mt-1 text-2xl font-bold text-text">{doc.title}</h1>
          {payload.share.label && (
            <p className="mt-1 text-sm text-text-muted">{payload.share.label}</p>
          )}
          <p className="mt-2 text-xs text-text-muted">
            {doc.doc_type} · {doc.number || `#${doc.id}`} · статус {doc.status}
          </p>
          <p
            className={`mt-3 inline-block rounded-lg px-3 py-1 text-sm font-semibold ${
              doc.payment_status === "paid"
                ? "bg-secondary/15 text-secondary"
                : doc.payment_status === "partial"
                  ? "bg-amber-500/15 text-amber-800"
                  : "bg-primary/10 text-primary"
            }`}
          >
            {paymentLabel}
          </p>
        </header>

        <section className="rounded-2xl border border-border bg-surface p-6 shadow-sm space-y-4">
          <div className="flex flex-wrap gap-6 text-sm">
            <div>
              <p className="text-xs text-text-muted">Сумма</p>
              <p className="font-semibold text-text">
                {doc.amount} {doc.currency}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Оплачено</p>
              <p className="font-semibold text-text">
                {doc.paid_total} {doc.currency}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-muted">К оплате</p>
              <p className="font-semibold text-text">
                {doc.balance_due} {doc.currency}
              </p>
            </div>
            {doc.organization_name && (
              <div>
                <p className="text-xs text-text-muted">Организация</p>
                <p className="font-semibold text-text">{doc.organization_name}</p>
              </div>
            )}
            {doc.person_name && (
              <div>
                <p className="text-xs text-text-muted">Контакт</p>
                <p className="font-semibold text-text">{doc.person_name}</p>
              </div>
            )}
            {doc.due_date && (
              <div>
                <p className="text-xs text-text-muted">Срок</p>
                <p className="font-semibold text-text">{doc.due_date}</p>
              </div>
            )}
          </div>

          {doc.body && (
            <div className="whitespace-pre-wrap text-sm text-text">{doc.body}</div>
          )}

          {doc.payments?.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-text-muted">
                Платежи
              </p>
              <ul className="space-y-1 text-sm">
                {doc.payments.map((payment, index) => (
                  <li
                    key={`${payment.paid_at}-${index}`}
                    className="flex justify-between rounded border border-border px-3 py-2"
                  >
                    <span>{payment.paid_at}</span>
                    <span className="font-medium">
                      {payment.amount} {payment.currency}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {doc.line_items?.length > 0 && (
            <ul className="space-y-1 text-sm">
              {doc.line_items.map((item, index) => (
                <li key={index} className="rounded border border-border px-3 py-2">
                  {JSON.stringify(item)}
                </li>
              ))}
            </ul>
          )}

          {message && (
            <p className="text-sm text-secondary" role="status">
              {message}
            </p>
          )}
          <ErrorMessage message={error} />

          <div className="flex flex-wrap gap-2">
            {payload.share.allow_pdf && token && (
              <a
                href={publicCrmDocumentPdfUrl(token)}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-border px-3 py-2 text-sm font-semibold text-primary"
              >
                Скачать PDF
              </a>
            )}
            {doc.can_approve && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void approve()}
                className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {busy ? "Принятие…" : "Принять документ"}
              </button>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
