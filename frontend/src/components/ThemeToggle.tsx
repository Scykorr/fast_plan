import { useTheme, type ThemePreference } from "../context/ThemeContext";

const CYCLE: ThemePreference[] = ["light", "dark", "system"];

function nextPreference(current: ThemePreference): ThemePreference {
  const index = CYCLE.indexOf(current);
  return CYCLE[(index + 1) % CYCLE.length];
}

function labelFor(preference: ThemePreference): string {
  if (preference === "light") {
    return "Светлая тема";
  }
  if (preference === "dark") {
    return "Тёмная тема";
  }
  return "Как в системе";
}

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { preference, theme, setTheme } = useTheme();
  const upcoming = nextPreference(preference);

  return (
    <button
      type="button"
      onClick={() => setTheme(upcoming)}
      className={[
        "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-cream text-text transition-colors hover:border-primary hover:text-primary",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      aria-label={`Тема: ${labelFor(preference)}. Переключить на: ${labelFor(upcoming)}`}
      title={`${labelFor(preference)} → ${labelFor(upcoming)}`}
    >
      {preference === "system" ? (
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" aria-hidden>
          <rect
            x="3"
            y="4"
            width="18"
            height="12"
            rx="2"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <path
            d="M8 20h8M12 16v4"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      ) : theme === "light" ? (
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" aria-hidden>
          <path
            d="M21 14.3A9 9 0 1 1 9.7 3 7 7 0 0 0 21 14.3Z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" aria-hidden>
          <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.8" />
          <path
            d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      )}
    </button>
  );
}
