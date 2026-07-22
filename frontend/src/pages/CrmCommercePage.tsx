import { useCallback, useEffect, useState, type FormEvent } from "react";

import { parseApiError } from "../api/errors";
import type { CrmChannelConnection, CrmDocument } from "../api/crm";
import { ErrorMessage } from "../components/ErrorMessage";
import { useCrmApi } from "../hooks/useCrmApi";
import { useLocale } from "../context/LocaleContext";
import { useWorkspace } from "../context/WorkspaceContext";

export function CrmCommercePage() {
  const crmApi = useCrmApi();
  const { formatMoney } = useLocale();
  const { workspaceEpoch } = useWorkspace();
  const [channels, setChannels] = useState<CrmChannelConnection[]>([]);
  const [documents, setDocuments] = useState<CrmDocument[]>([]);
  const [arAp, setArAp] = useState<Awaited<
    ReturnType<NonNullable<typeof crmApi>["getArAp"]>
  > | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [docForm, setDocForm] = useState({
    doc_type: "quote",
    title: "",
    amount: "",
    number: "",
    body: "",
  });
  const [imapForm, setImapForm] = useState({
    name: "IMAP inbox",
    host: "",
    username: "",
    password: "",
    port: "993",
  });
  const [tgForm, setTgForm] = useState({
    name: "Telegram bot",
    bot_token: "",
    webhook_secret: "",
  });

  const load = useCallback(async () => {
    if (!crmApi) return;
    try {
      const [ch, docs, ar] = await Promise.all([
        crmApi.listChannels(),
        crmApi.listDocuments(),
        crmApi.getArAp(),
      ]);
      setChannels(ch);
      setDocuments(docs);
      setArAp(ar);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить коммерцию/каналы"));
    }
  }, [crmApi]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const createDoc = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi || !docForm.title.trim()) return;
    try {
      await crmApi.createDocument({
        doc_type: docForm.doc_type,
        title: docForm.title.trim(),
        number: docForm.number,
        amount: docForm.amount || 0,
        body: docForm.body,
        status: "draft",
      });
      setDocForm({ ...docForm, title: "", amount: "", number: "", body: "" });
      setMessage("Документ создан");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать документ"));
    }
  };

  const createImap = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi) return;
    try {
      await crmApi.createChannel({
        provider: "imap",
        name: imapForm.name,
        config: {
          host: imapForm.host,
          username: imapForm.username,
          password: imapForm.password,
          port: Number(imapForm.port) || 993,
          use_ssl: true,
          folder: "INBOX",
        },
      });
      setMessage("IMAP-канал добавлен");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить IMAP"));
    }
  };

  const createTelegram = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi) return;
    try {
      await crmApi.createChannel({
        provider: "telegram",
        name: tgForm.name,
        config: {
          bot_token: tgForm.bot_token,
          webhook_secret: tgForm.webhook_secret || crypto.randomUUID().slice(0, 16),
        },
      });
      setMessage("Telegram-канал добавлен");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить Telegram"));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">Коммерция и омниканал</h1>
        <p className="mt-1 text-sm text-text-muted">
          КП/счета/договоры → PDF, оплаты, AR; IMAP и Telegram → Activity
        </p>
      </div>
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      {message && <p className="text-sm text-secondary">{message}</p>}

      {arAp && (
        <section className="rounded-xl border border-border bg-surface p-4">
          <h2 className="text-sm font-semibold text-text">AR lite</h2>
          <p className="mt-2 text-sm text-text">
            Открытая дебиторка: {formatMoney(arAp.ar_open_amount)} ({arAp.ar_open_count}{" "}
            счетов) · оплачено: {formatMoney(arAp.invoices_paid_amount)}
          </p>
        </section>
      )}

      <section className="rounded-xl border border-border bg-surface p-4 space-y-3">
        <h2 className="text-sm font-semibold text-text">Документы</h2>
        <form onSubmit={(e) => void createDoc(e)} className="grid gap-2 sm:grid-cols-4">
          <select
            value={docForm.doc_type}
            onChange={(e) => setDocForm({ ...docForm, doc_type: e.target.value })}
            className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
          >
            <option value="quote">КП</option>
            <option value="invoice">Счёт</option>
            <option value="contract">Договор</option>
          </select>
          <input
            value={docForm.title}
            onChange={(e) => setDocForm({ ...docForm, title: e.target.value })}
            placeholder="Название"
            className="rounded border border-border bg-surface px-2 py-1.5 text-sm sm:col-span-2"
            required
          />
          <input
            value={docForm.amount}
            onChange={(e) => setDocForm({ ...docForm, amount: e.target.value })}
            placeholder="Сумма"
            className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
          />
          <input
            value={docForm.number}
            onChange={(e) => setDocForm({ ...docForm, number: e.target.value })}
            placeholder="Номер"
            className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
          />
          <input
            value={docForm.body}
            onChange={(e) => setDocForm({ ...docForm, body: e.target.value })}
            placeholder="Текст"
            className="rounded border border-border bg-surface px-2 py-1.5 text-sm sm:col-span-2"
          />
          <button
            type="submit"
            className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
          >
            Создать
          </button>
        </form>
        <ul className="space-y-2">
          {documents.map((doc) => (
            <li
              key={doc.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border px-3 py-2 text-sm"
            >
              <div>
                <p className="font-medium text-text">
                  {doc.doc_type} · {doc.number || `#${doc.id}`} · {doc.title}
                </p>
                <p className="text-xs text-text-muted">
                  {doc.status} · {formatMoney(Number(doc.amount))} · оплачено{" "}
                  {formatMoney(doc.paid_total)}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="rounded border border-border px-2 py-1 text-xs"
                  onClick={() =>
                    void crmApi
                      ?.renderDocumentPdf(doc.id)
                      .then(load)
                      .catch((err) =>
                        setError(parseApiError(err, "PDF не сгенерирован")),
                      )
                  }
                >
                  PDF
                </button>
                {doc.pdf_url && (
                  <a
                    href={doc.pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded border border-border px-2 py-1 text-xs text-primary"
                  >
                    Открыть
                  </a>
                )}
                {doc.doc_type === "invoice" && doc.status !== "paid" && (
                  <button
                    type="button"
                    className="rounded border border-border px-2 py-1 text-xs"
                    onClick={() =>
                      void crmApi
                        ?.createDocumentPayment(doc.id, {
                          amount: doc.amount,
                          paid_at: new Date().toISOString().slice(0, 10),
                        })
                        .then(() => {
                          setMessage("Оплата записана");
                          return load();
                        })
                        .catch((err) =>
                          setError(parseApiError(err, "Не удалось записать оплату")),
                        )
                    }
                  >
                    Оплатить
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
          <h2 className="text-sm font-semibold text-text">IMAP / Gmail IMAP</h2>
          <form onSubmit={(e) => void createImap(e)} className="space-y-2">
            {(["name", "host", "username", "password", "port"] as const).map((key) => (
              <input
                key={key}
                value={imapForm[key]}
                onChange={(e) => setImapForm({ ...imapForm, [key]: e.target.value })}
                placeholder={key}
                type={key === "password" ? "password" : "text"}
                className="w-full rounded border border-border bg-surface px-2 py-1.5 text-sm"
              />
            ))}
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
            >
              Добавить IMAP
            </button>
          </form>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
          <h2 className="text-sm font-semibold text-text">Telegram bot</h2>
          <form onSubmit={(e) => void createTelegram(e)} className="space-y-2">
            <input
              value={tgForm.name}
              onChange={(e) => setTgForm({ ...tgForm, name: e.target.value })}
              placeholder="name"
              className="w-full rounded border border-border bg-surface px-2 py-1.5 text-sm"
            />
            <input
              value={tgForm.bot_token}
              onChange={(e) => setTgForm({ ...tgForm, bot_token: e.target.value })}
              placeholder="bot_token"
              className="w-full rounded border border-border bg-surface px-2 py-1.5 text-sm"
            />
            <input
              value={tgForm.webhook_secret}
              onChange={(e) =>
                setTgForm({ ...tgForm, webhook_secret: e.target.value })
              }
              placeholder="webhook_secret (optional)"
              className="w-full rounded border border-border bg-surface px-2 py-1.5 text-sm"
            />
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
            >
              Добавить Telegram
            </button>
          </form>
        </div>
      </section>

      <section className="rounded-xl border border-border bg-surface p-4">
        <h2 className="text-sm font-semibold text-text">Каналы</h2>
        <ul className="mt-2 space-y-2">
          {channels.map((ch) => (
            <li
              key={ch.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border px-3 py-2 text-sm"
            >
              <div>
                <p className="font-medium text-text">
                  {ch.provider} · {ch.name}
                </p>
                <p className="text-xs text-text-muted">
                  {ch.is_active ? "active" : "off"}
                  {ch.last_synced_at
                    ? ` · sync ${new Date(ch.last_synced_at).toLocaleString("ru-RU")}`
                    : ""}
                  {ch.last_error ? ` · err: ${ch.last_error}` : ""}
                </p>
                {ch.provider === "telegram" && ch.config.webhook_secret ? (
                  <p className="text-xs text-text-muted">
                    webhook: /api/crm/channels/telegram/{String(ch.config.webhook_secret)}/
                  </p>
                ) : null}
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="rounded border border-border px-2 py-1 text-xs"
                  onClick={() =>
                    void crmApi
                      ?.syncChannel(ch.id)
                      .then((res) => {
                        setMessage(`Синк: +${res.created}`);
                        return load();
                      })
                      .catch((err) => setError(parseApiError(err, "Синк не удался")))
                  }
                >
                  Sync
                </button>
                <button
                  type="button"
                  className="rounded border border-border px-2 py-1 text-xs text-text-muted"
                  onClick={() =>
                    void crmApi
                      ?.deleteChannel(ch.id)
                      .then(load)
                      .catch((err) => setError(parseApiError(err, "Удаление не удалось")))
                  }
                >
                  Удалить
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
