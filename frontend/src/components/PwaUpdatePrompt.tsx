import { useRegisterSW } from "virtual:pwa-register/react";

export function PwaUpdatePrompt() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_swUrl, registration) {
      if (registration) {
        setInterval(() => {
          void registration.update();
        }, 60 * 60 * 1000);
      }
    },
  });

  if (!needRefresh) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm rounded-xl border border-border bg-surface p-4 shadow-lg">
      <p className="text-sm font-medium text-text">Доступна новая версия</p>
      <p className="mt-1 text-xs text-text-muted">
        Обновите приложение, чтобы получить последние изменения.
      </p>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-hover"
          onClick={() => void updateServiceWorker(true)}
        >
          Обновить
        </button>
        <button
          type="button"
          className="rounded-lg border border-border px-3 py-1.5 text-xs text-text-muted hover:bg-cream"
          onClick={() => setNeedRefresh(false)}
        >
          Позже
        </button>
      </div>
    </div>
  );
}
