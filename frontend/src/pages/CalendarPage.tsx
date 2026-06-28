import { useCallback, useEffect, useState } from "react";

import type { Contact } from "../api/calendar";
import { BirthdayCalendar } from "../components/calendar/BirthdayCalendar";
import { ContactForm } from "../components/calendar/ContactForm";
import { useAuth } from "../context/AuthContext";
import { useCalendarApi } from "../hooks/useCalendarApi";

export function CalendarPage() {
  const { accessToken } = useAuth();
  const calendarApi = useCalendarApi();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const loadContacts = useCallback(async () => {
    if (!calendarApi) {
      return;
    }
    const data = await calendarApi.getContacts();
    setContacts(data);
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
    await calendarApi.createContact(data);
    await loadContacts();
    setRefreshKey((value) => value + 1);
    setShowForm(false);
  };

  const handleDeleteContact = async (contactId: number) => {
    if (!calendarApi || !window.confirm("Удалить контакт?")) {
      return;
    }
    await calendarApi.deleteContact(contactId);
    await loadContacts();
    setRefreshKey((value) => value + 1);
  };

  if (!accessToken) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text">Календарь</h1>
          <p className="mt-1 text-sm text-text-muted">
            Дни рождения друзей и близких
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

      <BirthdayCalendar token={accessToken} refreshKey={refreshKey} />

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
    </div>
  );
}
