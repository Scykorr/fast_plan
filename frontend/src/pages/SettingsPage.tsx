import { useAuth } from "../context/AuthContext";

export function SettingsPage() {
  const { user } = useAuth();

  return (
    <div>
      <h1 className="text-3xl font-bold text-text">Настройки</h1>
      <div className="mt-6 max-w-lg rounded-xl border border-border bg-surface p-6">
        <dl className="space-y-4 text-sm">
          <div>
            <dt className="text-text-muted">Email</dt>
            <dd className="mt-1 font-medium">{user?.email}</dd>
          </div>
          <div>
            <dt className="text-text-muted">Имя пользователя</dt>
            <dd className="mt-1 font-medium">{user?.username}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
