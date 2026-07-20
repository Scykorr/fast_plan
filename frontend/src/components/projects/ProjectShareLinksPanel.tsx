import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../../api/errors";
import type { ShareLink } from "../../api/projects";
import { ErrorMessage } from "../ErrorMessage";
import { useProjectsApi } from "../../hooks/useProjectsApi";

type Props = {
  projectId: number;
};

export function ProjectShareLinksPanel({ projectId }: Props) {
  const projectsApi = useProjectsApi();
  const [links, setLinks] = useState<ShareLink[]>([]);
  const [label, setLabel] = useState("");
  const [allowChat, setAllowChat] = useState(false);
  const [chatCanPost, setChatCanPost] = useState(false);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!projectsApi) {
      return;
    }
    try {
      setLinks(await projectsApi.getShareLinks(projectId));
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить ссылки"));
    }
  }, [projectsApi, projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async () => {
    if (!projectsApi) {
      return;
    }
    setCreating(true);
    setError("");
    try {
      await projectsApi.createShareLink(projectId, {
        label: label.trim(),
        allow_chat: allowChat,
        chat_can_post: allowChat && chatCanPost,
      });
      setLabel("");
      setAllowChat(false);
      setChatCanPost(false);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать ссылку"));
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (linkId: number) => {
    if (!projectsApi) {
      return;
    }
    try {
      await projectsApi.revokeShareLink(projectId, linkId);
      await load();
    } catch (err) {
      setError(parseApiError(err, "Не удалось отозвать ссылку"));
    }
  };

  const copyLink = async (token: string) => {
    const url = `${window.location.origin}/share/${token}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopiedToken(token);
      window.setTimeout(() => setCopiedToken(null), 2000);
    } catch {
      setError("Не удалось скопировать ссылку");
    }
  };

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <h2 className="text-lg font-semibold text-text">Гостевые ссылки</h2>
      <p className="mt-1 text-sm text-text-muted">
        Статус-отчёт для стейкхолдеров; опционально — доступ к чату проекта
      </p>
      {error && (
        <div className="mt-3">
          <ErrorMessage message={error} onDismiss={() => setError("")} />
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        <input
          type="text"
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          placeholder="Метка (необязательно)"
          className="min-w-[200px] flex-1 rounded-lg border border-border bg-cream px-3 py-2 text-sm"
        />
        <label className="flex items-center gap-2 text-sm text-text">
          <input
            type="checkbox"
            checked={allowChat}
            onChange={(event) => {
              setAllowChat(event.target.checked);
              if (!event.target.checked) {
                setChatCanPost(false);
              }
            }}
          />
          Чат
        </label>
        <label className="flex items-center gap-2 text-sm text-text">
          <input
            type="checkbox"
            checked={chatCanPost}
            disabled={!allowChat}
            onChange={(event) => setChatCanPost(event.target.checked)}
          />
          Гость может писать
        </label>
        <button
          type="button"
          disabled={creating}
          onClick={() => void handleCreate()}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
        >
          {creating ? "Создание..." : "Создать ссылку"}
        </button>
      </div>
      {links.length === 0 ? (
        <p className="mt-4 text-sm text-text-muted">Активных ссылок пока нет</p>
      ) : (
        <ul className="mt-4 space-y-2">
          {links.map((link) => (
            <li
              key={link.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-cream px-3 py-2 text-sm"
            >
              <div>
                <p className="font-medium text-text">
                  {link.label || "Без метки"}
                  {link.allow_chat ? " · чат" : ""}
                  {link.chat_can_post ? " · гость пишет" : ""}
                </p>
                <p className="text-xs text-text-muted">
                  Создана {new Date(link.created_at).toLocaleString("ru-RU")}
                  {link.last_accessed_at
                    ? ` · просмотр ${new Date(link.last_accessed_at).toLocaleString("ru-RU")}`
                    : ""}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => void copyLink(link.token)}
                  className="text-xs font-medium text-primary hover:underline"
                >
                  {copiedToken === link.token ? "Скопировано" : "Копировать URL"}
                </button>
                <button
                  type="button"
                  onClick={() => void handleRevoke(link.id)}
                  className="text-xs text-text-muted hover:underline"
                >
                  Отозвать
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
