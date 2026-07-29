import { useCallback, useEffect, useState, type FormEvent } from "react";

import { parseApiError } from "../api/errors";
import type {
  CrmCashflowForecast,
  CrmChannelConnection,
  CrmDocument,
  CrmIntegrationConnector,
  CrmPnl,
} from "../api/crm";
import { ErrorMessage } from "../components/ErrorMessage";
import { useCrmApi } from "../hooks/useCrmApi";
import { useLocale } from "../context/LocaleContext";
import { useWorkspace } from "../context/WorkspaceContext";

const CONNECTOR_PROVIDERS = [
  { value: "stripe", label: "Stripe" },
  { value: "onec", label: "1С" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "sms", label: "SMS" },
  { value: "telephony", label: "Telephony / PBX" },
] as const;

export function CrmCommercePage() {
  const crmApi = useCrmApi();
  const { formatMoney } = useLocale();
  const { workspaceEpoch } = useWorkspace();
  const [channels, setChannels] = useState<CrmChannelConnection[]>([]);
  const [connectors, setConnectors] = useState<CrmIntegrationConnector[]>([]);
  const [documents, setDocuments] = useState<CrmDocument[]>([]);
  const [arAp, setArAp] = useState<Awaited<
    ReturnType<NonNullable<typeof crmApi>["getArAp"]>
  > | null>(null);
  const [cashflow, setCashflow] = useState<CrmCashflowForecast | null>(null);
  const [pnl, setPnl] = useState<CrmPnl | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [connectorForm, setConnectorForm] = useState({
    provider: "stripe",
    name: "",
    webhook_secret: "",
    secret_key: "",
    access_token: "",
    verify_token: "",
    api_key: "",
    api_salt: "",
    from_number: "",
    pbx: "generic",
    extension: "",
    ari_base_url: "",
    ari_user: "",
    ari_password: "",
    ari_app: "fast-plan",
    endpoint: "",
    context: "from-internal",
    pending_json: "",
  });
  const [smsTo, setSmsTo] = useState("");
  const [smsBody, setSmsBody] = useState("");
  const [dialTo, setDialTo] = useState("");
  const [dialNote, setDialNote] = useState("");
  const [docForm, setDocForm] = useState({
    doc_type: "quote",
    title: "",
    amount: "",
    number: "",
    body: "",
    due_date: "",
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
  const [igForm, setIgForm] = useState({
    name: "Instagram",
    verify_token: "",
    webhook_secret: "",
  });
  const [vkForm, setVkForm] = useState({
    name: "VK",
    confirmation_code: "",
    secret_key: "",
    webhook_secret: "",
  });

  const load = useCallback(async () => {
    if (!crmApi) return;
    try {
      const [ch, docs, ar, cf, pnlRow, cons] = await Promise.all([
        crmApi.listChannels(),
        crmApi.listDocuments(),
        crmApi.getArAp(),
        crmApi.getCashflowForecast(90),
        crmApi.getPnl(),
        crmApi.listConnectors(),
      ]);
      setChannels(ch);
      setDocuments(docs);
      setArAp(ar);
      setCashflow(cf);
      setPnl(pnlRow);
      setConnectors(cons);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить коммерцию/каналы"));
    }
  }, [crmApi]);

  useEffect(() => {
    void load();
  }, [load, workspaceEpoch]);

  const createConnector = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi || !connectorForm.name.trim()) return;
    const config: Record<string, unknown> = {};
    if (connectorForm.webhook_secret) {
      config.webhook_secret = connectorForm.webhook_secret;
    }
    if (connectorForm.provider === "stripe" && connectorForm.secret_key) {
      config.secret_key = connectorForm.secret_key;
    }
    if (connectorForm.provider === "whatsapp") {
      if (connectorForm.access_token) config.access_token = connectorForm.access_token;
      if (connectorForm.verify_token) config.verify_token = connectorForm.verify_token;
    }
    if (connectorForm.provider === "sms") {
      if (connectorForm.api_key) config.api_key = connectorForm.api_key;
      if (connectorForm.from_number) config.from_number = connectorForm.from_number;
    }
    if (connectorForm.provider === "telephony") {
      config.pbx = connectorForm.pbx || "generic";
      if (connectorForm.api_key) config.api_key = connectorForm.api_key;
      if (connectorForm.api_salt) config.api_salt = connectorForm.api_salt;
      if (connectorForm.extension) config.extension = connectorForm.extension;
      if (connectorForm.from_number) config.from_number = connectorForm.from_number;
      if (connectorForm.ari_base_url) config.ari_base_url = connectorForm.ari_base_url;
      if (connectorForm.ari_user) config.ari_user = connectorForm.ari_user;
      if (connectorForm.ari_password) config.ari_password = connectorForm.ari_password;
      if (connectorForm.endpoint) config.endpoint = connectorForm.endpoint;
      if (connectorForm.endpoint && (connectorForm.pbx === "beeline" || connectorForm.pbx === "mts" || connectorForm.pbx === "generic")) {
        config.dial_url = connectorForm.endpoint;
      }
      if (connectorForm.context) config.context = connectorForm.context;
      if (connectorForm.ari_app) config.ari_app = connectorForm.ari_app;
    }
    if (connectorForm.provider === "onec" && connectorForm.pending_json.trim()) {
      try {
        config.pending_documents = JSON.parse(connectorForm.pending_json);
      } catch {
        setError("pending_documents: невалидный JSON");
        return;
      }
    }
    try {
      await crmApi.createConnector({
        provider: connectorForm.provider,
        name: connectorForm.name.trim(),
        config,
      });
      setConnectorForm({
        ...connectorForm,
        name: "",
        webhook_secret: "",
        secret_key: "",
        access_token: "",
        verify_token: "",
        api_key: "",
        from_number: "",
        pending_json: "",
      });
      setMessage("Коннектор создан");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать коннектор"));
    }
  };

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
        due_date: docForm.due_date || null,
        status: docForm.doc_type === "bill" || docForm.doc_type === "invoice"
          ? "sent"
          : "draft",
      });
      setDocForm({
        doc_type: docForm.doc_type,
        title: "",
        amount: "",
        number: "",
        body: "",
        due_date: "",
      });
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

  const createInstagram = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi) return;
    try {
      await crmApi.createChannel({
        provider: "instagram",
        name: igForm.name,
        config: {
          verify_token: igForm.verify_token || "fast-plan",
          webhook_secret:
            igForm.webhook_secret || crypto.randomUUID().slice(0, 16),
        },
      });
      setMessage("Instagram-канал добавлен");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить Instagram"));
    }
  };

  const createVk = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi) return;
    try {
      await crmApi.createChannel({
        provider: "vk",
        name: vkForm.name,
        config: {
          confirmation_code: vkForm.confirmation_code || "ok",
          secret: vkForm.secret_key,
          secret_key: vkForm.secret_key,
          webhook_secret:
            vkForm.webhook_secret || crypto.randomUUID().slice(0, 16),
        },
      });
      setMessage("VK-канал добавлен");
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить VK"));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text">Коммерция и омниканал</h1>
        <p className="mt-1 text-sm text-text-muted">
          КП/счета/акты/счета поставщиков → PDF, оплаты, AR/AP, cashflow; IMAP,
          Telegram, Instagram, VK → Activity
        </p>
      </div>
      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      {message && <p className="text-sm text-secondary">{message}</p>}

      {arAp && (
        <section className="grid gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-border bg-surface p-4">
            <h2 className="text-sm font-semibold text-text">Дебиторка (AR)</h2>
            <p className="mt-2 text-sm text-text">
              Открыто: {formatMoney(arAp.ar_open_amount)} ({arAp.ar_open_count}{" "}
              счетов) · оплачено: {formatMoney(arAp.invoices_paid_amount)}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-4">
            <h2 className="text-sm font-semibold text-text">Кредиторка (AP)</h2>
            <p className="mt-2 text-sm text-text">
              Открыто: {formatMoney(arAp.ap_open_amount)} ({arAp.ap_open_count}{" "}
              счетов поставщиков) · оплачено:{" "}
              {formatMoney(arAp.bills_paid_amount)}
            </p>
            <p className="mt-1 text-xs text-text-muted">
              Expense ledger (org/deal): {formatMoney(arAp.expense_ledger_amount)}
            </p>
          </div>
        </section>
      )}

      {cashflow && (
        <section className="rounded-xl border border-border bg-surface p-4 space-y-3">
          <h2 className="text-sm font-semibold text-text">
            Cashflow forecast ({cashflow.horizon_days}д)
          </h2>
          <div className="grid gap-2 sm:grid-cols-3">
            {cashflow.buckets.map((bucket) => (
              <div
                key={bucket.label}
                className="rounded-lg border border-border bg-cream/40 px-3 py-2 text-sm"
              >
                <p className="font-medium text-text">{bucket.label}</p>
                <p className="text-xs text-text-muted">
                  +{formatMoney(bucket.inflow)} / −{formatMoney(bucket.outflow)}
                </p>
                <p className="text-xs text-text-muted">
                  сделки: {formatMoney(bucket.deal_forecast)}
                </p>
                <p className="mt-1 font-semibold text-text">
                  net {formatMoney(bucket.net)}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {pnl && (
        <section className="rounded-xl border border-border bg-surface p-4 space-y-2">
          <h2 className="text-sm font-semibold text-text">P&amp;L (Finance ledger)</h2>
          <p className="text-sm text-text">
            Доход {formatMoney(pnl.income_total)} · расход{" "}
            {formatMoney(pnl.expense_total)} · прибыль{" "}
            <span className="font-semibold">{formatMoney(pnl.profit)}</span>
          </p>
          {pnl.by_organization.length > 0 && (
            <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto text-xs text-text-muted">
              {pnl.by_organization.slice(0, 8).map((row) => (
                <li key={row.organization_id}>
                  {row.organization_name}: +{formatMoney(row.income)} / −
                  {formatMoney(row.expense)} = {formatMoney(row.profit)}
                </li>
              ))}
            </ul>
          )}
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
            <option value="invoice">Счёт (AR)</option>
            <option value="bill">Счёт поставщика (AP)</option>
            <option value="act">Акт</option>
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
            type="date"
            value={docForm.due_date}
            onChange={(e) => setDocForm({ ...docForm, due_date: e.target.value })}
            className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
            title="Срок"
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
        <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
          <h2 className="text-sm font-semibold text-text">Instagram</h2>
          <form onSubmit={(e) => void createInstagram(e)} className="space-y-2">
            <input
              value={igForm.name}
              onChange={(e) => setIgForm({ ...igForm, name: e.target.value })}
              placeholder="name"
              className="w-full rounded border border-border bg-surface px-2 py-1.5 text-sm"
            />
            <input
              value={igForm.verify_token}
              onChange={(e) =>
                setIgForm({ ...igForm, verify_token: e.target.value })
              }
              placeholder="verify_token (Meta hub.verify_token)"
              className="w-full rounded border border-border bg-surface px-2 py-1.5 text-sm"
            />
            <input
              value={igForm.webhook_secret}
              onChange={(e) =>
                setIgForm({ ...igForm, webhook_secret: e.target.value })
              }
              placeholder="webhook_secret (optional)"
              className="w-full rounded border border-border bg-surface px-2 py-1.5 text-sm"
            />
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
            >
              Добавить Instagram
            </button>
          </form>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
          <h2 className="text-sm font-semibold text-text">VK Callback</h2>
          <form onSubmit={(e) => void createVk(e)} className="space-y-2">
            <input
              value={vkForm.name}
              onChange={(e) => setVkForm({ ...vkForm, name: e.target.value })}
              placeholder="name"
              className="w-full rounded border border-border bg-surface px-2 py-1.5 text-sm"
            />
            <input
              value={vkForm.confirmation_code}
              onChange={(e) =>
                setVkForm({ ...vkForm, confirmation_code: e.target.value })
              }
              placeholder="confirmation_code"
              className="w-full rounded border border-border bg-surface px-2 py-1.5 text-sm"
            />
            <input
              value={vkForm.secret_key}
              onChange={(e) =>
                setVkForm({ ...vkForm, secret_key: e.target.value })
              }
              placeholder="secret_key (optional)"
              className="w-full rounded border border-border bg-surface px-2 py-1.5 text-sm"
            />
            <input
              value={vkForm.webhook_secret}
              onChange={(e) =>
                setVkForm({ ...vkForm, webhook_secret: e.target.value })
              }
              placeholder="webhook_secret (optional)"
              className="w-full rounded border border-border bg-surface px-2 py-1.5 text-sm"
            />
            <button
              type="submit"
              className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
            >
              Добавить VK
            </button>
          </form>
        </div>
      </section>

      <section className="rounded-xl border border-border bg-surface p-4 space-y-3">
        <h2 className="text-sm font-semibold text-text">
          Коннекторы (Stripe / 1С / WhatsApp / SMS / Telephony)
        </h2>
        <form
          onSubmit={(e) => void createConnector(e)}
          className="grid gap-2 sm:grid-cols-3"
        >
          <select
            value={connectorForm.provider}
            onChange={(e) =>
              setConnectorForm({ ...connectorForm, provider: e.target.value })
            }
            className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
          >
            {CONNECTOR_PROVIDERS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <input
            value={connectorForm.name}
            onChange={(e) =>
              setConnectorForm({ ...connectorForm, name: e.target.value })
            }
            placeholder="Название"
            className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
            required
          />
          <input
            value={connectorForm.webhook_secret}
            onChange={(e) =>
              setConnectorForm({
                ...connectorForm,
                webhook_secret: e.target.value,
              })
            }
            placeholder="webhook_secret (опц.)"
            className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
          />
          {connectorForm.provider === "stripe" && (
            <input
              value={connectorForm.secret_key}
              onChange={(e) =>
                setConnectorForm({ ...connectorForm, secret_key: e.target.value })
              }
              placeholder="secret_key"
              type="password"
              className="rounded border border-border bg-surface px-2 py-1.5 text-sm sm:col-span-2"
            />
          )}
          {connectorForm.provider === "whatsapp" && (
            <>
              <input
                value={connectorForm.access_token}
                onChange={(e) =>
                  setConnectorForm({
                    ...connectorForm,
                    access_token: e.target.value,
                  })
                }
                placeholder="access_token"
                className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
              />
              <input
                value={connectorForm.verify_token}
                onChange={(e) =>
                  setConnectorForm({
                    ...connectorForm,
                    verify_token: e.target.value,
                  })
                }
                placeholder="verify_token"
                className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
              />
            </>
          )}
          {connectorForm.provider === "sms" && (
            <>
              <input
                value={connectorForm.api_key}
                onChange={(e) =>
                  setConnectorForm({ ...connectorForm, api_key: e.target.value })
                }
                placeholder="api_key"
                className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
              />
              <input
                value={connectorForm.from_number}
                onChange={(e) =>
                  setConnectorForm({
                    ...connectorForm,
                    from_number: e.target.value,
                  })
                }
                placeholder="from_number"
                className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
              />
            </>
          )}
          {connectorForm.provider === "telephony" && (
            <>
              <select
                value={connectorForm.pbx}
                onChange={(e) =>
                  setConnectorForm({ ...connectorForm, pbx: e.target.value })
                }
                className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
              >
                <option value="asterisk">Asterisk ARI</option>
                <option value="mango">Mango Office</option>
                <option value="beeline">Beeline Cloud</option>
                <option value="mts">MTS / Communicator</option>
                <option value="generic">Generic dial_url</option>
              </select>
              {connectorForm.pbx === "mango" && (
                <>
                  <input
                    value={connectorForm.api_key}
                    onChange={(e) =>
                      setConnectorForm({
                        ...connectorForm,
                        api_key: e.target.value,
                      })
                    }
                    placeholder="vpbx_api_key"
                    className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
                  />
                  <input
                    value={connectorForm.api_salt}
                    onChange={(e) =>
                      setConnectorForm({
                        ...connectorForm,
                        api_salt: e.target.value,
                      })
                    }
                    placeholder="vpbx_api_salt"
                    type="password"
                    className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
                  />
                  <input
                    value={connectorForm.extension}
                    onChange={(e) =>
                      setConnectorForm({
                        ...connectorForm,
                        extension: e.target.value,
                      })
                    }
                    placeholder="extension (внутр.)"
                    className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
                  />
                </>
              )}
              {connectorForm.pbx === "asterisk" && (
                <>
                  <input
                    value={connectorForm.ari_base_url}
                    onChange={(e) =>
                      setConnectorForm({
                        ...connectorForm,
                        ari_base_url: e.target.value,
                      })
                    }
                    placeholder="ari_base_url (…/ari)"
                    className="rounded border border-border bg-surface px-2 py-1.5 text-sm sm:col-span-2"
                  />
                  <input
                    value={connectorForm.ari_user}
                    onChange={(e) =>
                      setConnectorForm({
                        ...connectorForm,
                        ari_user: e.target.value,
                      })
                    }
                    placeholder="ari_user"
                    className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
                  />
                  <input
                    value={connectorForm.ari_password}
                    onChange={(e) =>
                      setConnectorForm({
                        ...connectorForm,
                        ari_password: e.target.value,
                      })
                    }
                    placeholder="ari_password"
                    type="password"
                    className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
                  />
                  <input
                    value={connectorForm.endpoint}
                    onChange={(e) =>
                      setConnectorForm({
                        ...connectorForm,
                        endpoint: e.target.value,
                      })
                    }
                    placeholder="endpoint (PJSIP/100)"
                    className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
                  />
                  <input
                    value={connectorForm.ari_app}
                    onChange={(e) =>
                      setConnectorForm({
                        ...connectorForm,
                        ari_app: e.target.value,
                      })
                    }
                    placeholder="ari_app (Stasis)"
                    className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
                  />
                  <input
                    value={connectorForm.context}
                    onChange={(e) =>
                      setConnectorForm({
                        ...connectorForm,
                        context: e.target.value,
                      })
                    }
                    placeholder="context"
                    className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
                  />
                </>
              )}
              {connectorForm.pbx === "generic" && (
                <input
                  value={connectorForm.from_number}
                  onChange={(e) =>
                    setConnectorForm({
                      ...connectorForm,
                      from_number: e.target.value,
                    })
                  }
                  placeholder="from_number (опц.)"
                  className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
                />
              )}
              {(connectorForm.pbx === "beeline" || connectorForm.pbx === "mts") && (
                <>
                  <input
                    value={connectorForm.extension}
                    onChange={(e) =>
                      setConnectorForm({
                        ...connectorForm,
                        extension: e.target.value,
                      })
                    }
                    placeholder="extension"
                    className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
                  />
                  <input
                    value={connectorForm.from_number}
                    onChange={(e) =>
                      setConnectorForm({
                        ...connectorForm,
                        from_number: e.target.value,
                      })
                    }
                    placeholder="from_number"
                    className="rounded border border-border bg-surface px-2 py-1.5 text-sm"
                  />
                  <input
                    value={connectorForm.endpoint}
                    onChange={(e) =>
                      setConnectorForm({
                        ...connectorForm,
                        endpoint: e.target.value,
                      })
                    }
                    placeholder="dial_url"
                    className="rounded border border-border bg-surface px-2 py-1.5 text-sm sm:col-span-2"
                  />
                </>
              )}
            </>
          )}
          {connectorForm.provider === "onec" && (
            <textarea
              value={connectorForm.pending_json}
              onChange={(e) =>
                setConnectorForm({
                  ...connectorForm,
                  pending_json: e.target.value,
                })
              }
              placeholder='pending_documents JSON: [{"id":"1","title":"Счёт","amount":"100"}]'
              rows={2}
              className="rounded border border-border bg-surface px-2 py-1.5 text-sm sm:col-span-3"
            />
          )}
          <button
            type="submit"
            className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
          >
            Добавить коннектор
          </button>
        </form>

        <ul className="space-y-2">
          {connectors.length === 0 ? (
            <li className="text-sm text-text-muted">Коннекторов пока нет</li>
          ) : (
            connectors.map((item) => (
              <li
                key={item.id}
                className="rounded-lg border border-border px-3 py-2 text-sm space-y-1"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium text-text">
                      {item.provider} · {item.name}
                    </p>
                    <p className="text-xs text-text-muted break-all">
                      webhook: {item.webhook_path}
                    </p>
                    {item.last_error ? (
                      <p className="text-xs text-danger">{item.last_error}</p>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(item.provider === "stripe" || item.provider === "onec") && (
                      <button
                        type="button"
                        className="rounded border border-border px-2 py-1 text-xs"
                        onClick={() =>
                          void crmApi
                            ?.syncConnector(item.id)
                            .then((res) => {
                              setMessage(`Sync ${item.provider}: +${res.created ?? 0}`);
                              return load();
                            })
                            .catch((err) =>
                              setError(parseApiError(err, "Sync не удался")),
                            )
                        }
                      >
                        Sync
                      </button>
                    )}
                    <button
                      type="button"
                      className="rounded border border-border px-2 py-1 text-xs text-text-muted"
                      onClick={() =>
                        void crmApi
                          ?.deleteConnector(item.id)
                          .then(load)
                          .catch((err) =>
                            setError(parseApiError(err, "Удаление не удалось")),
                          )
                      }
                    >
                      Удалить
                    </button>
                  </div>
                </div>
                {item.provider === "sms" && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    <input
                      value={smsTo}
                      onChange={(e) => setSmsTo(e.target.value)}
                      placeholder="to"
                      className="rounded border border-border bg-cream px-2 py-1 text-xs"
                    />
                    <input
                      value={smsBody}
                      onChange={(e) => setSmsBody(e.target.value)}
                      placeholder="текст SMS"
                      className="min-w-[10rem] flex-1 rounded border border-border bg-cream px-2 py-1 text-xs"
                    />
                    <button
                      type="button"
                      className="rounded border border-border px-2 py-1 text-xs"
                      onClick={() =>
                        void crmApi
                          ?.sendConnectorSms(item.id, {
                            to: smsTo,
                            body: smsBody,
                          })
                          .then(() => {
                            setMessage("SMS записано");
                            setSmsBody("");
                          })
                          .catch((err) =>
                            setError(parseApiError(err, "SMS не отправлено")),
                          )
                      }
                    >
                      Send SMS
                    </button>
                  </div>
                )}
                {item.provider === "telephony" && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    <input
                      value={dialTo}
                      onChange={(e) => setDialTo(e.target.value)}
                      placeholder="to"
                      className="rounded border border-border bg-cream px-2 py-1 text-xs"
                    />
                    <input
                      value={dialNote}
                      onChange={(e) => setDialNote(e.target.value)}
                      placeholder="заметка к звонку"
                      className="min-w-[10rem] flex-1 rounded border border-border bg-cream px-2 py-1 text-xs"
                    />
                    <button
                      type="button"
                      className="rounded border border-border px-2 py-1 text-xs"
                      onClick={() =>
                        void crmApi
                          ?.sendConnectorDial(item.id, {
                            to: dialTo,
                            note: dialNote,
                          })
                          .then(() => {
                            setMessage("Звонок записан");
                            setDialNote("");
                          })
                          .catch((err) =>
                            setError(parseApiError(err, "Dial не выполнен")),
                          )
                      }
                    >
                      Dial
                    </button>
                    <button
                      type="button"
                      className="rounded border border-border px-2 py-1 text-xs"
                      onClick={() =>
                        void crmApi
                          ?.getConnectorAriBridge(item.id)
                          .then((res) => {
                            setMessage(
                              res.ready
                                ? `ARI bridge ready · ${res.command}`
                                : `ARI bridge: ${res.detail || res.hint || "not ready"}`,
                            );
                          })
                          .catch((err) =>
                            setError(parseApiError(err, "ARI bridge status failed")),
                          )
                      }
                    >
                      ARI bridge status
                    </button>
                  </div>
                )}
              </li>
            ))
          )}
        </ul>
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
                {ch.provider === "instagram" && ch.config.webhook_secret ? (
                  <p className="text-xs text-text-muted">
                    webhook: /api/crm/channels/instagram/{String(ch.config.webhook_secret)}/
                  </p>
                ) : null}
                {ch.provider === "vk" && ch.config.webhook_secret ? (
                  <p className="text-xs text-text-muted">
                    webhook: /api/crm/channels/vk/{String(ch.config.webhook_secret)}/
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
