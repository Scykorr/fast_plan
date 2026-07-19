import type { BoardFlowAnalytics } from "../../api/kanban";

export function FlowAnalytics({ data }: { data: BoardFlowAnalytics }) {
  const maxRemaining = Math.max(
    1,
    ...data.burndown.map((point) => Math.max(point.remaining, point.ideal)),
  );
  const maxVelocity = Math.max(1, ...data.velocity.map((point) => point.completed));

  return (
    <div className="mt-8 grid gap-4 lg:grid-cols-2">
      <section className="rounded-xl border border-border bg-surface p-5">
        <h2 className="font-semibold text-text">Burndown · 14 дней</h2>
        <div className="mt-4 flex h-40 items-end gap-1" aria-label="Burndown chart">
          {data.burndown.map((point) => (
            <div
              key={point.date}
              className="group relative flex h-full flex-1 items-end"
              title={`${point.date}: ${point.remaining} осталось`}
            >
              <div
                className="w-full rounded-t bg-primary/80"
                style={{ height: `${(point.remaining / maxRemaining) * 100}%` }}
              />
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-text-muted">
          Остаток карточек; завершённой считается последняя колонка доски.
        </p>
      </section>
      <section className="rounded-xl border border-border bg-surface p-5">
        <h2 className="font-semibold text-text">Velocity · 4 недели</h2>
        <div className="mt-4 flex h-40 items-end gap-4" aria-label="Velocity chart">
          {data.velocity.map((point) => (
            <div key={point.week_start} className="flex h-full flex-1 flex-col justify-end">
              <span className="mb-1 text-center text-xs font-semibold text-text">
                {point.completed}
              </span>
              <div
                className="rounded-t bg-secondary"
                style={{
                  height: `${Math.max(4, (point.completed / maxVelocity) * 100)}%`,
                }}
              />
              <span className="mt-1 truncate text-center text-[10px] text-text-muted">
                {point.week_start.slice(5)}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
