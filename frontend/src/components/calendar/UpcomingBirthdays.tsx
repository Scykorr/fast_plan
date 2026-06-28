import type { UpcomingBirthday } from "../../api/calendar";

type UpcomingBirthdaysProps = {
  items: UpcomingBirthday[];
  loading?: boolean;
};

function formatDaysUntil(days: number) {
  if (days === 0) {
    return "Сегодня!";
  }
  if (days === 1) {
    return "Завтра";
  }
  return `Через ${days} дн.`;
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
  });
}

export function UpcomingBirthdays({ items, loading }: UpcomingBirthdaysProps) {
  if (loading) {
    return <p className="text-sm text-text-muted">Загрузка ближайших дней рождения...</p>;
  }

  if (items.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        Пока нет контактов. Добавьте их в разделе «Календарь».
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li
          key={item.contact_id}
          className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3"
        >
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary/20 text-sm font-semibold text-secondary">
              {item.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="font-medium text-text">{item.name}</p>
              <p className="text-xs text-text-muted">
                {item.relation ? `${item.relation} · ` : ""}
                {formatDate(item.next_date)}
              </p>
            </div>
          </div>
          <span className="rounded-full bg-accent/15 px-3 py-1 text-xs font-semibold text-accent">
            {formatDaysUntil(item.days_until)}
          </span>
        </li>
      ))}
    </ul>
  );
}
