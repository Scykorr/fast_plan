import { type FormEvent, useState } from "react";

import { parseApiError } from "../../api/errors";

const inputClass =
  "w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20";

type InviteMemberFormProps = {
  onSubmit: (email: string, role: string) => Promise<void>;
  onCancel?: () => void;
};

export function InviteMemberForm({ onSubmit, onCancel }: InviteMemberFormProps) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("editor");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!email.trim()) {
      setError("Укажите email");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await onSubmit(email.trim().toLowerCase(), role);
      setEmail("");
      setRole("editor");
    } catch (err) {
      setError(parseApiError(err, "Не удалось отправить приглашение"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      noValidate
      onSubmit={(event) => void handleSubmit(event)}
      className="rounded-xl border border-dashed border-border p-4"
    >
      <h3 className="text-sm font-semibold text-text">Пригласить участника</h3>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block text-text-muted">Email</span>
          <input
            aria-label="Email"
            type="email"
            required
            className={inputClass}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-text-muted">Роль</span>
          <select
            aria-label="Роль"
            className={inputClass}
            value={role}
            onChange={(event) => setRole(event.target.value)}
          >
            <option value="editor">Editor</option>
            <option value="viewer">Viewer</option>
            <option value="owner">Owner</option>
          </select>
        </label>
      </div>
      {error && (
        <p className="mt-2 text-sm text-primary" role="alert">
          {error}
        </p>
      )}
      <div className="mt-3 flex gap-2">
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {loading ? "Отправка..." : "Пригласить"}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-border px-3 py-1.5 text-sm text-text-muted"
          >
            Отмена
          </button>
        )}
      </div>
    </form>
  );
}
