import { useCallback, useEffect, useState, type FormEvent } from "react";

import { parseApiError } from "../api/errors";
import type { CrmActivity, CrmOrganization, CrmPerson } from "../api/crm";
import { ErrorMessage } from "../components/ErrorMessage";
import { useCrmApi } from "../hooks/useCrmApi";
import { useWorkspace } from "../context/WorkspaceContext";

const ACTIVITY_KINDS: Array<CrmActivity["kind"]> = [
  "note",
  "call",
  "meeting",
  "email",
  "other",
];

const KIND_LABELS: Record<CrmActivity["kind"], string> = {
  note: "Заметка",
  call: "Звонок",
  meeting: "Встреча",
  email: "Email",
  other: "Другое",
};

export function ClientsPage() {
  const crmApi = useCrmApi();
  const { workspaceEpoch } = useWorkspace();
  const [tab, setTab] = useState<"people" | "orgs">("people");
  const [query, setQuery] = useState("");
  const [people, setPeople] = useState<CrmPerson[]>([]);
  const [orgs, setOrgs] = useState<CrmOrganization[]>([]);
  const [selectedPerson, setSelectedPerson] = useState<CrmPerson | null>(null);
  const [selectedOrg, setSelectedOrg] = useState<CrmOrganization | null>(null);
  const [activities, setActivities] = useState<CrmActivity[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const [personForm, setPersonForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    job_title: "",
    organization_id: "" as number | "",
  });
  const [orgForm, setOrgForm] = useState({ name: "", website: "", industry: "" });
  const [activityForm, setActivityForm] = useState({
    kind: "note" as CrmActivity["kind"],
    subject: "",
    body: "",
  });

  const loadDirectory = useCallback(async () => {
    if (!crmApi) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [peopleData, orgData] = await Promise.all([
        crmApi.listPeople(query),
        crmApi.listOrganizations(query),
      ]);
      setPeople(peopleData);
      setOrgs(orgData);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить CRM"));
    } finally {
      setLoading(false);
    }
  }, [crmApi, query]);

  useEffect(() => {
    void loadDirectory();
  }, [loadDirectory, workspaceEpoch]);

  const loadActivities = useCallback(async () => {
    if (!crmApi) {
      return;
    }
    try {
      if (selectedPerson) {
        setActivities(await crmApi.listActivities({ person_id: selectedPerson.id }));
      } else if (selectedOrg) {
        setActivities(
          await crmApi.listActivities({ organization_id: selectedOrg.id }),
        );
      } else {
        setActivities([]);
      }
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить активности"));
    }
  }, [crmApi, selectedPerson, selectedOrg]);

  useEffect(() => {
    void loadActivities();
  }, [loadActivities]);

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
        job_title: personForm.job_title.trim(),
        organization_id: personForm.organization_id || null,
      });
      setPersonForm({
        full_name: "",
        email: "",
        phone: "",
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
      await loadActivities();
    } catch (err) {
      setError(parseApiError(err, "Не удалось добавить активность"));
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

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text">Клиенты</h1>
          <p className="mt-1 text-sm text-text-muted">
            Directory компаний и контактов (Project CRM · P6a)
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

      <div className="flex flex-wrap gap-2">
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
          className="min-w-[12rem] flex-1 rounded-lg border border-border bg-cream px-3 py-1.5 text-sm"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
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
                    setPersonForm((prev) => ({ ...prev, full_name: event.target.value }))
                  }
                  placeholder="ФИО *"
                  className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  required
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={personForm.email}
                    onChange={(event) =>
                      setPersonForm((prev) => ({ ...prev, email: event.target.value }))
                    }
                    placeholder="Email"
                    className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  />
                  <input
                    value={personForm.phone}
                    onChange={(event) =>
                      setPersonForm((prev) => ({ ...prev, phone: event.target.value }))
                    }
                    placeholder="Телефон"
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
                    {people.map((person) => (
                      <li key={person.id}>
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedPerson(person);
                            setSelectedOrg(null);
                          }}
                          className={`w-full px-4 py-3 text-left hover:bg-cream ${
                            selectedPerson?.id === person.id ? "bg-cream" : ""
                          }`}
                        >
                          <p className="font-medium text-text">{person.full_name}</p>
                          <p className="text-xs text-text-muted">
                            {[person.email, person.job_title, person.organizations[0]?.name]
                              .filter(Boolean)
                              .join(" · ") || "Без деталей"}
                          </p>
                        </button>
                      </li>
                    ))}
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
                      setOrgForm((prev) => ({ ...prev, website: event.target.value }))
                    }
                    placeholder="Сайт"
                    className="rounded-lg border border-border bg-cream px-3 py-2 text-sm"
                  />
                  <input
                    value={orgForm.industry}
                    onChange={(event) =>
                      setOrgForm((prev) => ({ ...prev, industry: event.target.value }))
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
                    {orgs.map((org) => (
                      <li key={org.id}>
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedOrg(org);
                            setSelectedPerson(null);
                          }}
                          className={`w-full px-4 py-3 text-left hover:bg-cream ${
                            selectedOrg?.id === org.id ? "bg-cream" : ""
                          }`}
                        >
                          <p className="font-medium text-text">{org.name}</p>
                          <p className="text-xs text-text-muted">
                            {[org.industry, `${org.people_count ?? 0} чел.`]
                              .filter(Boolean)
                              .join(" · ")}
                          </p>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>

        <div className="space-y-4 rounded-xl border border-border bg-surface p-4">
          <h2 className="text-lg font-semibold text-text">
            {selectedPerson
              ? selectedPerson.full_name
              : selectedOrg
                ? selectedOrg.name
                : "Карточка"}
          </h2>
          {!selectedPerson && !selectedOrg ? (
            <p className="text-sm text-text-muted">
              Выберите контакт или компанию, чтобы увидеть timeline.
            </p>
          ) : (
            <>
              {selectedPerson && (
                <div className="space-y-1 text-sm text-text-muted">
                  {selectedPerson.email && <p>{selectedPerson.email}</p>}
                  {selectedPerson.phone && <p>{selectedPerson.phone}</p>}
                  {selectedPerson.job_title && <p>{selectedPerson.job_title}</p>}
                  {selectedPerson.notes && (
                    <p className="whitespace-pre-wrap text-text">{selectedPerson.notes}</p>
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
                    <p className="whitespace-pre-wrap text-text">{selectedOrg.notes}</p>
                  )}
                </div>
              )}

              <form onSubmit={(event) => void createActivity(event)} className="space-y-2 border-t border-border pt-3">
                <h3 className="text-sm font-semibold text-text">Активность</h3>
                <div className="flex flex-wrap gap-2">
                  <select
                    value={activityForm.kind}
                    onChange={(event) =>
                      setActivityForm((prev) => ({
                        ...prev,
                        kind: event.target.value as CrmActivity["kind"],
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
                    setActivityForm((prev) => ({ ...prev, body: event.target.value }))
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
        </div>
      </div>
    </div>
  );
}
