import { type FormEvent, useState } from "react";

type ContactFormProps = {
  onSubmit: (data: {
    name: string;
    relation: string;
    birth_date: string;
    notes: string;
  }) => Promise<void>;
  onCancel?: () => void;
};

export function ContactForm({ onSubmit, onCancel }: ContactFormProps) {
  const [name, setName] = useState("");
  const [relation, setRelation] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await onSubmit({
        name: name.trim(),
        relation: relation.trim(),
        birth_date: birthDate,
        notes: notes.trim(),
      });
      setName("");
      setRelation("");
      setBirthDate("");
      setNotes("");
    } catch {
      setError("Не удалось сохранить контакт");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-border bg-surface p-5"
    >
      <h2 className="text-lg font-semibold text-text">Новый контакт</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="contact-name" className="mb-1 block text-sm font-medium">
            Имя
          </label>
          <input
            id="contact-name"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label htmlFor="contact-relation" className="mb-1 block text-sm font-medium">
            Кто это
          </label>
          <input
            id="contact-relation"
            placeholder="друг, мама, коллега"
            value={relation}
            onChange={(e) => setRelation(e.target.value)}
            className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label htmlFor="contact-birthday" className="mb-1 block text-sm font-medium">
            Дата рождения
          </label>
          <input
            id="contact-birthday"
            type="date"
            required
            value={birthDate}
            onChange={(e) => setBirthDate(e.target.value)}
            className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label htmlFor="contact-notes" className="mb-1 block text-sm font-medium">
            Заметки
          </label>
          <input
            id="contact-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      {error && (
        <p className="mt-3 text-sm text-primary" role="alert">
          {error}
        </p>
      )}

      <div className="mt-4 flex gap-2">
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {loading ? "Сохранение..." : "Добавить"}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-border px-4 py-2 text-sm text-text-muted hover:bg-cream"
          >
            Отмена
          </button>
        )}
      </div>
    </form>
  );
}
