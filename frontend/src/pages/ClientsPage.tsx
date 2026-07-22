import { useCallback, useEffect, useState, type FormEvent } from "react";

import { parseApiError } from "../api/errors";
import type {
  CrmActivity,
  CrmActivityKind,
  CrmAttachment,
  CrmComment,
  CrmOrganization,
  CrmPerson,
  CrmSegment,
  CrmTag,
} from "../api/crm";
import type { WorkspaceMember } from "../api/workspace";
import { ErrorMessage } from "../components/ErrorMessage";
import { useCrmApi } from "../hooks/useCrmApi";
import { useWorkspace } from "../context/WorkspaceContext";
import { useWorkspaceApi } from "../hooks/useWorkspaceApi";

const ACTIVITY_KINDS: CrmActivityKind[] = [
  "note",
  "call",
  "meeting",
  "email",
  "invoice",
  "order",
  "other",
];

const KIND_LABELS: Record<CrmActivityKind, string> = {
  note: "Заметка",
  call: "Звонок",
  meeting: "Встреча",
  email: "Email",
  invoice: "Счёт",
  order: "Заказ",
  other: "Другое",
};

const STALE_DEFAULT = 14;

function staleLabel(days: number | null | undefined) {
  if (days == null) {
    return "Нет касаний";
  }
  if (days >= STALE_DEFAULT) {
    return `Нет касаний ${days} дн.`;
  }
  return `Касание ${days} дн. назад`;
}

export function ClientsPage() {
  const crmApi = useCrmApi();
  const workspaceApi = useWorkspaceApi();
  const { workspaceEpoch } = useWorkspace();
  const [tab, setTab] = useState<"people" | "orgs">("people");
  const [query, setQuery] = useState("");
  const [staleOnly, setStaleOnly] = useState(false);
  const [people, setPeople] = useState<CrmPerson[]>([]);
  const [orgs, setOrgs] = useState<CrmOrganization[]>([]);
  const [tags, setTags] = useState<CrmTag[]>([]);
  const [segments, setSegments] = useState<CrmSegment[]>([]);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [filterTagId, setFilterTagId] = useState<number | "">("");
  const [filterSegmentId, setFilterSegmentId] = useState<number | "">("");
  const [selectedPerson, setSelectedPerson] = useState<CrmPerson | null>(null);
  const [selectedOrg, setSelectedOrg] = useState<CrmOrganization | null>(null);
  const [cardTab, setCardTab] = useState<
    "overview" | "history" | "notes" | "docs"
  >("overview");
  const [activities, setActivities] = useState<CrmActivity[]>([]);
  const [comments, setComments] = useState<CrmComment[]>([]);
  const [attachments, setAttachments] = useState<CrmAttachment[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const [personForm, setPersonForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    telegram: "",
    whatsapp: "",
    job_title: "",
    organization_id: "" as number | "",
  });
  const [orgForm, setOrgForm] = useState({ name: "", website: "", industry: "" });
  const [activityForm, setActivityForm] = useState({
    kind: "note" as CrmActivityKind,
    subject: "",
    body: "",
  });
  const [commentBody, setCommentBody] = useState("");
  const [tagDraft, setTagDraft] = useState("");
  const [segmentForm, setSegmentForm] = useState({
    name: "",
    kind: "rule" as "manual" | "rule",
    stale_days: String(STALE_DEFAULT),
  });

  const listParams = useCallback(
    () => ({
      q: query,
      tag_id: filterTagId || undefined,
      segment_id: filterSegmentId || undefined,
      stale_days: staleOnly ? STALE_DEFAULT : undefined,
    }),
    [query, filterTagId, filterSegmentId, staleOnly],
  );

  const loadDirectory = useCallback(async () => {
    if (!crmApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const params = listParams();
      const [peopleData, orgData, tagData, segmentData] = await Promise.all([
        crmApi.listPeople(params),
        crmApi.listOrganizations(params),
        crmApi.listTags(),
        crmApi.listSegments(),
      ]);
      setPeople(peopleData);
      setOrgs(orgData);
      setTags(tagData);
      setSegments(segmentData);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить CRM"));
    } finally {
      setLoading(false);
    }
  }, [crmApi, listParams]);

  useEffect(() => {
    void loadDirectory();
  }, [loadDirectory, workspaceEpoch]);

  useEffect(() => {
    if (!workspaceApi) {
      return;
    }
    void workspaceApi
      .getMembers()
      .then(setMembers)
      .catch((err) => {
        setError(parseApiError(err, "Не удалось загрузить участников"));
      });
  }, [workspaceApi, workspaceEpoch]);

  const assignOwner = async (ownerId: number | null) => {
    if (!crmApi) {
      return;
    }
    try {
      if (selectedPerson) {
        const updated = await crmApi.patchPerson(selectedPerson.id, {
          owner_id: ownerId,
        });
        setSelectedPerson(updated);
      } else if (selectedOrg) {
        const updated = await crmApi.patchOrganization(selectedOrg.id, {
          owner_id: ownerId,
        });
        setSelectedOrg(updated);
      }
      await loadDirectory();
    } catch (err) {
      setError(parseApiError(err, "Не удалось назначить менеджера"));
    }
  };

  const loadCardSide = useCallback(async () => {
    if (!crmApi) {
      return;
    }
    const target = selectedPerson
      ? { person_id: selectedPerson.id }
      : selectedOrg
        ? { organization_id: selectedOrg.id }
        : null;
    if (!target) {
      setActivities([]);
      setComments([]);
      setAttachments([]);
      return;
    }
    try {
      const [acts, notes, files] = await Promise.all([
        crmApi.listActivities(target),
        crmApi.listComments(target),
        crmApi.listAttachments(target),
      ]);
      setActivities(acts);
      setComments(notes);
      setAttachments(files);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить карточку"));
    }
  }, [crmApi, selectedPerson, selectedOrg]);

  useEffect(() => {
    void loadCardSide();
  }, [loadCardSide]);

  const createPerson = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi || !personForm.full_name.trim()) {
      return;
    }
    try {
      await crmApi.createPerson({
        full_name: personForm.full_name.trim(),
        email: personForm.email.trim(),
        phone: personForm.phone.trim(),
        telegram: personForm.telegram.trim(),
        whatsapp: personForm.whatsapp.trim(),
        job_title: personForm.job_title.trim(),
        organization_id: personForm.organization_id || null,
      });
      setPersonForm({
        full_name: "",
        email: "",
        phone: "",
        telegram: "",
        whatsapp: "",
        job_title: "",
        organization_id: "",
      });
      await loadDirectory();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать контакт"));
    }
  };

  const createOrg = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi || !orgForm.name.trim()) {
      return;
    }
    try {
      await crmApi.createOrganization({
        name: orgForm.name.trim(),
        website: orgForm.website.trim(),
        industry: orgForm.industry.trim(),
      });
      setOrgForm({ name: "", website: "", industry: "" });
      await loadDirectory();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать организацию"));
    }
  };

  const createActivity = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi || !activityForm.subject.trim()) {
      return;
    }
    if (!selectedPerson && !selectedOrg) {
      setError("Выберите человека или организацию");
      return;
    }
    try {
      await crmApi.createActivity({
        kind: activityForm.kind,
        subject: activityForm.subject.trim(),
        body: activityForm.body.trim(),
        person_id: selectedPerson?.id ?? null,
        organization_id: selectedOrg?.id ?? null,
      });
      setActivityForm({ kind: "note", subject: "", body: "" });
      await loadCardSide();
      await loadDirectory();
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить активность"));
    }
  };

  const createComment = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi || !commentBody.trim() || (!selectedPerson && !selectedOrg)) {
      return;
    }
    try {
      await crmApi.createComment({
        body: commentBody.trim(),
        person_id: selectedPerson?.id ?? null,
        organization_id: selectedOrg?.id ?? null,
      });
      setCommentBody("");
      await loadCardSide();
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить комментарий"));
    }
  };

  const attachTag = async () => {
    if (!crmApi || !tagDraft.trim()) {
      return;
    }
    try {
      if (selectedPerson) {
        const tag = await crmApi.attachPersonTag(selectedPerson.id, {
          name: tagDraft.trim(),
        });
        setSelectedPerson({
          ...selectedPerson,
          tags: [...selectedPerson.tags.filter((t) => t.id !== tag.id), tag],
        });
      } else if (selectedOrg) {
        const tag = await crmApi.attachOrganizationTag(selectedOrg.id, {
          name: tagDraft.trim(),
        });
        setSelectedOrg({
          ...selectedOrg,
          tags: [...selectedOrg.tags.filter((t) => t.id !== tag.id), tag],
        });
      }
      setTagDraft("");
      await loadDirectory();
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить тег"));
    }
  };

  const uploadFile = async (file: File | null) => {
    if (!crmApi || !file || (!selectedPerson && !selectedOrg)) {
      return;
    }
    try {
      await crmApi.uploadAttachment({
        file,
        person_id: selectedPerson?.id,
        organization_id: selectedOrg?.id,
      });
      await loadCardSide();
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить файл"));
    }
  };

  const createSegment = async (event: FormEvent) => {
    event.preventDefault();
    if (!crmApi || !segmentForm.name.trim()) {
      return;
    }
    try {
      const staleDays = Number(segmentForm.stale_days) || STALE_DEFAULT;
      await crmApi.createSegment({
        name: segmentForm.name.trim(),
        kind: segmentForm.kind,
        rule:
          segmentForm.kind === "rule"
            ? { stale_days: staleDays }
            : {},
        person_ids: [],
        organization_ids: [],
      });
      setSegmentForm({
        name: "",
        kind: "rule",
        stale_days: String(STALE_DEFAULT),
      });
      await loadDirectory();
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать сегмент"));
    }
  };

  const importLegacy = async () => {
    if (!crmApi) {
      return;
    }
    try {
      const result = await crmApi.importLegacy();
      setMessage(
        `Импорт: контактов ${result.imported_contacts}, стейкхолдеров ${result.imported_stakeholders}`,
      );
      await loadDirectory();
    } catch (err) {
      setError(parseApiError(err, "Не удалось импортировать"));
    }
  };

  const selectPerson = (person: CrmPerson) => {
    setSelectedPerson(person);
    setSelectedOrg(null);
    setCardTab("overview");
  };

  const selectOrg = (org: CrmOrganization) => {
    setSelectedOrg(org);
    setSelectedPerson(null);
    setCardTab("overview");
  };

  const currentTags = selectedPerson?.tags ?? selectedOrg?.tags ?? [];
  const daysSince =
    selectedPerson?.days_since_touch ?? selectedOrg?.days_since_touch ?? null;
  const isStale = daysSince == null || daysSince >= STALE_DEFAULT;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text">Клиенты</h1>
          <p className="mt-1 text-sm text-text-muted">
            Карточка клиента · теги, сегменты, история, документы (P6b)
          </p>
        </div>
        <button
          type="button"
          onClick={() => void importLegacy()}
          className="rounded-lg border border-border bg-cream px-3 py-1.5 text-sm font-medium text-text hover:border-primary"
        >
          Импорт из Contact / Stakeholder
        </button>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError("")} />}
      {message && <p className="text-sm text-secondary">{message}</p>}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setTab("people")}
          className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
            tab === "people" ? "bg-primary text-white" : "bg-cream text-text"
          }`}
        >
          Люди
        </button>
        <button
          type="button"
          onClick={() => setTab("orgs")}
          className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
            tab === "orgs" ? "bg-primary text-white" : "bg-cream text-text"
          }`}
        >
          Компании
        </button>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Поиск…"
          className="min-w-[10rem] flex-1 rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
        />
        <select
          value={filterTagId}
          onChange={(event) =>
            setFilterTagId(event.target.value ? Number(event.target.value) : "")
          }
          className="rounded-lg border border-border bg-cream px-2 py-1.5 text-sm"
        >
          <option value="">Все теги</option>
          {tags.map((tag) => (
            <option key={tag.id} value={tag.id}>
              {tag.name}
            </option>
          ))}
        </select>
        <select
          value={filterSegmentId}
          onChange={(event) =>
            setFilterSegmentId(
              event.target.value ? Number(event.target.value) : "",
            )
          }
          className="rounded-lg border border-border bg-cream px-2 py-1.5 text-sm"
        >
          <option value="">Все сегменты</option>
          {segments.map((segment) => (
            <option key={segment.id} value={segment.id}>
              {segment.name}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-1.5 text-sm text-text-muted">
          <input
            type="checkbox"
            checked={staleOnly}
            onChange={(event) => setStaleOnly(event.target.checked)}
          />
          Нет касаний ≥{STALE_DEFAULT} дн.
        </label>
      </div>

      <form
        onSubmit={(event) => void createSegment(event)}
        className="flex flex-wrap items-end gap-2 rounded-xl border border-border bg-surface p-3"
      >
        <div>
          <label className="text-xs text-text-muted">Сегмент</label>
          <input
            value={segmentForm.name}
            onChange={(event) =>
              setSegmentForm((prev) => ({ ...prev, name: event.target.value }))
            }
            placeholder="VIP без касаний"
            className="mt-0.5 block rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="text-xs text-text-muted">Правило: дни</label>
          <input
            value={segmentForm.stale_days}
            onChange={(event) =>
              setSegmentForm((prev) => ({
                ...prev,
                stale_days: event.target.value,
              }))
            }
            className="mt-0.5 block w-20 rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
          />
        </div>
        <button
          type="submit"
          className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
        >
          Создать rule-сегмент
        </button>
      </form>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <div className="space-y-4">
          {tab === "people" ? (
            <>
              <form
                onSubmit={(event) => void createPerson(event)}
                className="space-y-2 rounded-xl border border-border bg-surface p-4"
              >
                <h2 className="text-sm font-semibold text-text">Новый контакт</h2>
                <input
                  value={personForm.full_name}
                  onChange={(event) =>
                    setPersonForm((prev) => ({
                      ...prev,
                      full_name: event.target.value,
                    }))
                  }
                  placeholder="ФИО *"
                  className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  required
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={personForm.email}
                    onChange={(event) =>
                      setPersonForm((prev) => ({
                        ...prev,
                        email: event.target.value,
                      }))
                    }
                    placeholder="Email"
                    className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  />
                  <input
                    value={personForm.phone}
                    onChange={(event) =>
                      setPersonForm((prev) => ({
                        ...prev,
                        phone: event.target.value,
                      }))
                    }
                    placeholder="Телефон"
                    className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={personForm.telegram}
                    onChange={(event) =>
                      setPersonForm((prev) => ({
                        ...prev,
                        telegram: event.target.value,
                      }))
                    }
                    placeholder="Telegram"
                    className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  />
                  <input
                    value={personForm.whatsapp}
                    onChange={(event) =>
                      setPersonForm((prev) => ({
                        ...prev,
                        whatsapp: event.target.value,
                      }))
                    }
                    placeholder="WhatsApp"
                    className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={personForm.job_title}
                    onChange={(event) =>
                      setPersonForm((prev) => ({
                        ...prev,
                        job_title: event.target.value,
                      }))
                    }
                    placeholder="Должность"
                    className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  />
                  <select
                    value={personForm.organization_id}
                    onChange={(event) =>
                      setPersonForm((prev) => ({
                        ...prev,
                        organization_id: event.target.value
                          ? Number(event.target.value)
                          : "",
                      }))
                    }
                    className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  >
                    <option value="">Без компании</option>
                    {orgs.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.name}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  type="submit"
                  className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
                >
                  Добавить
                </button>
              </form>

              <div className="rounded-xl border border-border bg-surface">
                {loading ? (
                  <p className="p-4 text-sm text-text-muted">Загрузка…</p>
                ) : people.length === 0 ? (
                  <p className="p-4 text-sm text-text-muted">Пока нет контактов</p>
                ) : (
                  <ul className="divide-y divide-border">
                    {people.map((person) => {
                      const stale =
                        person.days_since_touch == null ||
                        person.days_since_touch >= STALE_DEFAULT;
                      return (
                        <li key={person.id}>
                          <button
                            type="button"
                            onClick={() => selectPerson(person)}
                            className={`w-full px-4 py-3 text-left hover:bg-cream ${
                              selectedPerson?.id === person.id ? "bg-cream" : ""
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <p className="font-medium text-text">
                                {person.full_name}
                              </p>
                              {stale && (
                                <span className="shrink-0 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">
                                  {staleLabel(person.days_since_touch)}
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-text-muted">
                              {[
                                person.email,
                                person.telegram && `@${person.telegram.replace(/^@/, "")}`,
                                person.organizations[0]?.name,
                              ]
                                .filter(Boolean)
                                .join(" · ") || "Без деталей"}
                            </p>
                            {person.tags.length > 0 && (
                              <div className="mt-1 flex flex-wrap gap-1">
                                {person.tags.map((tag) => (
                                  <span
                                    key={tag.id}
                                    className="rounded px-1.5 py-0.5 text-[10px] text-white"
                                    style={{ backgroundColor: tag.color || "#3b82f6" }}
                                  >
                                    {tag.name}
                                  </span>
                                ))}
                              </div>
                            )}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </>
          ) : (
            <>
              <form
                onSubmit={(event) => void createOrg(event)}
                className="space-y-2 rounded-xl border border-border bg-surface p-4"
              >
                <h2 className="text-sm font-semibold text-text">Новая компания</h2>
                <input
                  value={orgForm.name}
                  onChange={(event) =>
                    setOrgForm((prev) => ({ ...prev, name: event.target.value }))
                  }
                  placeholder="Название *"
                  className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  required
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={orgForm.website}
                    onChange={(event) =>
                      setOrgForm((prev) => ({
                        ...prev,
                        website: event.target.value,
                      }))
                    }
                    placeholder="Сайт"
                    className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  />
                  <input
                    value={orgForm.industry}
                    onChange={(event) =>
                      setOrgForm((prev) => ({
                        ...prev,
                        industry: event.target.value,
                      }))
                    }
                    placeholder="Отрасль"
                    className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  />
                </div>
                <button
                  type="submit"
                  className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
                >
                  Добавить
                </button>
              </form>

              <div className="rounded-xl border border-border bg-surface">
                {loading ? (
                  <p className="p-4 text-sm text-text-muted">Загрузка…</p>
                ) : orgs.length === 0 ? (
                  <p className="p-4 text-sm text-text-muted">Пока нет компаний</p>
                ) : (
                  <ul className="divide-y divide-border">
                    {orgs.map((org) => {
                      const stale =
                        org.days_since_touch == null ||
                        org.days_since_touch >= STALE_DEFAULT;
                      return (
                        <li key={org.id}>
                          <button
                            type="button"
                            onClick={() => selectOrg(org)}
                            className={`w-full px-4 py-3 text-left hover:bg-cream ${
                              selectedOrg?.id === org.id ? "bg-cream" : ""
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <p className="font-medium text-text">{org.name}</p>
                              {stale && (
                                <span className="shrink-0 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">
                                  {staleLabel(org.days_since_touch)}
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-text-muted">
                              {[
                                org.industry,
                                `${org.people_count ?? 0} чел.`,
                                org.owner_email,
                              ]
                                .filter(Boolean)
                                .join(" · ")}
                            </p>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>

        <div className="space-y-4 rounded-xl border border-border bg-surface p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold text-text">
                {selectedPerson
                  ? selectedPerson.full_name
                  : selectedOrg
                    ? selectedOrg.name
                    : "Карточка"}
              </h2>
              {(selectedPerson || selectedOrg) && (
                <p
                  className={`mt-1 text-xs ${
                    isStale ? "font-medium text-amber-700 dark:text-amber-300" : "text-text-muted"
                  }`}
                >
                  {staleLabel(daysSince)}
                  {(selectedPerson?.owner_email || selectedOrg?.owner_email) &&
                    ` · менеджер ${selectedPerson?.owner_email ?? selectedOrg?.owner_email}`}
                </p>
              )}
            </div>
          </div>

          {!selectedPerson && !selectedOrg ? (
            <p className="text-sm text-text-muted">
              Выберите контакт или компанию: обзор, история, заметки, документы.
            </p>
          ) : (
            <>
              <div className="flex flex-wrap gap-1 border-b border-border pb-2">
                {(
                  [
                    ["overview", "Обзор"],
                    ["history", "История"],
                    ["notes", "Заметки"],
                    ["docs", "Документы"],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setCardTab(id)}
                    className={`rounded-lg px-2.5 py-1 text-xs font-medium ${
                      cardTab === id
                        ? "bg-primary text-white"
                        : "bg-cream text-text-muted"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {cardTab === "overview" && (
                <div className="space-y-3">
                  {selectedPerson && (
                    <div className="space-y-1 text-sm text-text-muted">
                      {selectedPerson.email && <p>Email: {selectedPerson.email}</p>}
                      {selectedPerson.phone && <p>Телефон: {selectedPerson.phone}</p>}
                      {selectedPerson.telegram && (
                        <p>Telegram: {selectedPerson.telegram}</p>
                      )}
                      {selectedPerson.whatsapp && (
                        <p>WhatsApp: {selectedPerson.whatsapp}</p>
                      )}
                      {selectedPerson.job_title && (
                        <p>Должность: {selectedPerson.job_title}</p>
                      )}
                      {selectedPerson.social_urls?.length > 0 && (
                        <ul className="list-inside list-disc">
                          {selectedPerson.social_urls.map((url) => (
                            <li key={url}>
                              <a
                                href={url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-primary hover:underline"
                              >
                                {url}
                              </a>
                            </li>
                          ))}
                        </ul>
                      )}
                      {selectedPerson.notes && (
                        <p className="whitespace-pre-wrap text-text">
                          {selectedPerson.notes}
                        </p>
                      )}
                    </div>
                  )}
                  {selectedOrg && (
                    <div className="space-y-1 text-sm text-text-muted">
                      {selectedOrg.website && (
                        <a
                          href={selectedOrg.website}
                          target="_blank"
                          rel="noreferrer"
                          className="text-primary hover:underline"
                        >
                          {selectedOrg.website}
                        </a>
                      )}
                      {selectedOrg.industry && <p>{selectedOrg.industry}</p>}
                      {selectedOrg.notes && (
                        <p className="whitespace-pre-wrap text-text">
                          {selectedOrg.notes}
                        </p>
                      )}
                    </div>
                  )}

                  <div>
                    <h3 className="text-sm font-semibold text-text">Менеджер</h3>
                    <select
                      value={
                        selectedPerson?.owner_id ?? selectedOrg?.owner_id ?? ""
                      }
                      onChange={(event) => {
                        const value = event.target.value;
                        void assignOwner(value ? Number(value) : null);
                      }}
                      className="mt-1 w-full rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
                    >
                      <option value="">Не назначен</option>
                      {members.map((member) => (
                        <option key={member.id} value={member.user_id}>
                          {member.email}
                          {member.crm_role ? ` (${member.crm_role})` : ""}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-text">Теги</h3>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {currentTags.length === 0 && (
                        <span className="text-xs text-text-muted">Нет тегов</span>
                      )}
                      {currentTags.map((tag) => (
                        <span
                          key={tag.id}
                          className="rounded px-1.5 py-0.5 text-[11px] text-white"
                          style={{ backgroundColor: tag.color || "#3b82f6" }}
                        >
                          {tag.name}
                        </span>
                      ))}
                    </div>
                    <div className="mt-2 flex gap-2">
                      <input
                        value={tagDraft}
                        onChange={(event) => setTagDraft(event.target.value)}
                        placeholder="Новый тег"
                        className="flex-1 rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
                      />
                      <button
                        type="button"
                        onClick={() => void attachTag()}
                        className="rounded-lg border border-border px-3 py-1.5 text-sm"
                      >
                        +
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {cardTab === "history" && (
                <>
                  <form
                    onSubmit={(event) => void createActivity(event)}
                    className="space-y-2"
                  >
                    <h3 className="text-sm font-semibold text-text">Активность</h3>
                    <div className="flex flex-wrap gap-2">
                      <select
                        value={activityForm.kind}
                        onChange={(event) =>
                          setActivityForm((prev) => ({
                            ...prev,
                            kind: event.target.value as CrmActivityKind,
                          }))
                        }
                        className="rounded-lg border border-border bg-cream px-2 py-1.5 text-sm"
                      >
                        {ACTIVITY_KINDS.map((kind) => (
                          <option key={kind} value={kind}>
                            {KIND_LABELS[kind]}
                          </option>
                        ))}
                      </select>
                      <input
                        value={activityForm.subject}
                        onChange={(event) =>
                          setActivityForm((prev) => ({
                            ...prev,
                            subject: event.target.value,
                          }))
                        }
                        placeholder="Тема *"
                        className="min-w-[10rem] flex-1 rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
                        required
                      />
                    </div>
                    <textarea
                      value={activityForm.body}
                      onChange={(event) =>
                        setActivityForm((prev) => ({
                          ...prev,
                          body: event.target.value,
                        }))
                      }
                      rows={2}
                      placeholder="Детали"
                      className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                    />
                    <button
                      type="submit"
                      className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
                    >
                      Записать
                    </button>
                  </form>
                  <ul className="max-h-80 space-y-2 overflow-y-auto border-t border-border pt-3">
                    {activities.length === 0 ? (
                      <li className="text-sm text-text-muted">Пока нет активностей</li>
                    ) : (
                      activities.map((activity) => (
                        <li
                          key={activity.id}
                          className="rounded-lg border border-border bg-cream/50 px-3 py-2 text-sm"
                        >
                          <div className="flex flex-wrap items-baseline justify-between gap-2">
                            <span className="font-medium text-text">
                              {KIND_LABELS[activity.kind]}: {activity.subject}
                            </span>
                            <time className="text-xs text-text-muted">
                              {new Date(activity.occurred_at).toLocaleString("ru-RU")}
                            </time>
                          </div>
                          {activity.body && (
                            <p className="mt-1 whitespace-pre-wrap text-text-muted">
                              {activity.body}
                            </p>
                          )}
                        </li>
                      ))
                    )}
                  </ul>
                </>
              )}

              {cardTab === "notes" && (
                <>
                  <form
                    onSubmit={(event) => void createComment(event)}
                    className="space-y-2"
                  >
                    <textarea
                      value={commentBody}
                      onChange={(event) => setCommentBody(event.target.value)}
                      rows={3}
                      placeholder="Комментарий…"
                      className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                      required
                    />
                    <button
                      type="submit"
                      className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white"
                    >
                      Добавить
                    </button>
                  </form>
                  <ul className="max-h-72 space-y-2 overflow-y-auto">
                    {comments.length === 0 ? (
                      <li className="text-sm text-text-muted">Нет комментариев</li>
                    ) : (
                      comments.map((comment) => (
                        <li
                          key={comment.id}
                          className="rounded-lg border border-border bg-cream/50 px-3 py-2 text-sm"
                        >
                          <p className="whitespace-pre-wrap text-text">{comment.body}</p>
                          <p className="mt-1 text-xs text-text-muted">
                            {comment.author_email ?? "—"} ·{" "}
                            {new Date(comment.created_at).toLocaleString("ru-RU")}
                          </p>
                        </li>
                      ))
                    )}
                  </ul>
                </>
              )}

              {cardTab === "docs" && (
                <>
                  <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-border bg-cream px-3 py-1.5 text-sm">
                    Загрузить файл
                    <input
                      type="file"
                      className="hidden"
                      onChange={(event) => {
                        const file = event.target.files?.[0] ?? null;
                        void uploadFile(file);
                        event.target.value = "";
                      }}
                    />
                  </label>
                  <ul className="mt-3 space-y-2">
                    {attachments.length === 0 ? (
                      <li className="text-sm text-text-muted">Нет файлов</li>
                    ) : (
                      attachments.map((file) => (
                        <li
                          key={file.id}
                          className="flex items-center justify-between gap-2 rounded-lg border border-border px-3 py-2 text-sm"
                        >
                          <a
                            href={file.url ?? "#"}
                            target="_blank"
                            rel="noreferrer"
                            className="text-primary hover:underline"
                          >
                            {file.name}
                          </a>
                          <span className="text-xs text-text-muted">
                            {Math.round(file.size / 1024)} КБ
                          </span>
                        </li>
                      ))
                    )}
                  </ul>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
