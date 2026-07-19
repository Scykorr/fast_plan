import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "../api/errors";
import { ErrorMessage } from "../components/ErrorMessage";
import type { Contact } from "../api/calendar";
import { WorkspaceCalendar } from "../components/calendar/WorkspaceCalendar";
import { ContactForm } from "../components/calendar/ContactForm";
import { useAuth } from "../context/AuthContext";
import { useCalendarApi } from "../hooks/useCalendarApi";
import { useConfirm } from "../hooks/useConfirm";

export function CalendarPage() {
  const { isAuthenticated } = useAuth();
  const calendarApi = useCalendarApi();
  const { confirm, dialog: confirmDialog } = useConfirm();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [showBirthdays, setShowBirthdays] = useState(true);
  const [showMilestones, setShowMilestones] = useState(true);
  const [error, setError] = useState("");

  const loadContacts = useCallback(async () => {
    if (!calendarApi) {
      return;
    }
    setError("");
    try {
      const data = await calendarApi.getContacts();
      setContacts(data);
    } catch (err) {
      setError(parseApiError(err, "Не удалось загрузить контакты"));
    }
  }, [calendarApi]);

  useEffect(() => {
    void loadContacts();
  }, [loadContacts]);

  const handleCreateContact = async (data: {
    name: string;
    relation: string;
    birth_date: string;
    notes: string;
  }) => {
    if (!calendarApi) {
      return;
    }
    try {
      await calendarApi.createContact(data);
      await loadContacts();
      setRefreshKey((value) => value + 1);
      setShowForm(false);
    } catch (err) {
      setError(parseApiError(err, "Не удалось создать контакт"));
      throw err;
    }
  };

  const handleDeleteContact = async (contactId: number) => {
    if (!calendarApi || !(await confirm("Удалить контакт?"))) {
      return;
    }
    try {
      await calendarApi.deleteContact(contactId);
      await loadContacts();
      setRefreshKey((value) => value + 1);
    } catch (err) {
      setError(parseApiError(err, "Не удалось удалить контакт"));
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="space-y-6">
      {error && (
        <ErrorMessage message={error} onDismiss={() => setError("")} />
      )}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text">Календарь</h1>
          <p className="mt-1 text-sm text-text-muted">
            Дни рождения и вехи проектов
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowForm((value) => !value)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover"
        >
          {showForm ? "Скрыть форму" : "+ Добавить контакт"}
        </button>
      </div>

      {showForm && (
        <ContactForm
          onSubmit={handleCreateContact}
          onCancel={() => setShowForm(false)}
        />
      )}

      <div className="flex flex-wrap gap-4 text-sm">
        <label className="flex items-center gap-2 text-text">
          <input
            type="checkbox"
            checked={showBirthdays}
            onChange={(event) => setShowBirthdays(event.target.checked)}
            className="rounded border-border text-primary"
          />
          Дни рождения
        </label>
        <label className="flex items-center gap-2 text-text">
          <input
            type="checkbox"
            checked={showMilestones}
            onChange={(event) => setShowMilestones(event.target.checked)}
            className="rounded border-border text-primary"
          />
          Вехи проектов
        </label>
      </div>

      <WorkspaceCalendar
        
        refreshKey={refreshKey}
        showBirthdays={showBirthdays}
        showMilestones={showMilestones}
      />

      <section>
        <h2 className="mb-3 text-lg font-semibold text-text">Контакты</h2>
        {contacts.length === 0 ? (
          <p className="text-sm text-text-muted">Список пуст</p>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2">
            {contacts.map((contact) => (
              <li
                key={contact.id}
                className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3"
              >
                <div>
                  <p className="font-medium text-text">{contact.name}</p>
                  <p className="text-xs text-text-muted">
                    {contact.relation ? `${contact.relation} · ` : ""}
                    {new Date(contact.birth_date).toLocaleDateString("ru-RU")}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void handleDeleteContact(contact.id)}
                  className="text-sm text-text-muted hover:text-primary"
                >
                  Удалить
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
      {confirmDialog}
    </div>
  );
}
