type ErrorMessageProps = {
  message: string;
  onDismiss?: () => void;
};

export function ErrorMessage({ message, onDismiss }: ErrorMessageProps) {
  if (!message) {
    return null;
  }

  return (
    <div
      role="alert"
      className="flex items-start justify-between gap-3 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 text-sm text-primary"
    >
      <span>{message}</span>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 text-primary/70 hover:text-primary"
          aria-label="Закрыть"
        >
          ×
        </button>
      )}
    </div>
  );
}
