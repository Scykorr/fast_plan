import Gantt from "frappe-gantt";
import { useEffect, useRef } from "react";

import type { ActivityDependency, ScheduleActivity } from "../../api/projects";

type GanttChartProps = {
  activities: ScheduleActivity[];
  dependencies: ActivityDependency[];
};

function buildDependenciesMap(dependencies: ActivityDependency[]) {
  const map = new Map<number, string[]>();
  for (const dep of dependencies) {
    const list = map.get(dep.successor_id) ?? [];
    list.push(`${dep.predecessor_id}${dep.dependency_type}`);
    map.set(dep.successor_id, list);
  }
  return map;
}

function customClassFor(activity: ScheduleActivity): string {
  const classes: string[] = [];
  if (activity.is_milestone) classes.push("bar-milestone");
  if (activity.capacity_hint?.overloaded) classes.push("bar-overloaded");
  return classes.join(" ");
}

export function GanttChart({ activities, dependencies }: GanttChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const ganttRef = useRef<Gantt | null>(null);
  const overloadedCount = activities.filter(
    (a) => a.capacity_hint?.overloaded,
  ).length;

  useEffect(() => {
    if (!containerRef.current || activities.length === 0) {
      return;
    }

    const depMap = buildDependenciesMap(dependencies);
    const tasks = activities
      .filter((activity) => activity.start_date && activity.end_date)
      .map((activity) => {
        const assignee = activity.assignee_name
          ? ` · ${activity.assignee_name}`
          : "";
        const overload = activity.capacity_hint?.hint
          ? ` · ${activity.capacity_hint.hint}`
          : "";
        return {
          id: String(activity.id),
          name: `${activity.code} ${activity.name}${assignee}${overload}`,
          start: activity.start_date!,
          end: activity.end_date!,
          progress: activity.progress,
          dependencies: (depMap.get(activity.id) ?? []).join(","),
          custom_class: customClassFor(activity),
        };
      });

    containerRef.current.innerHTML = "";
    ganttRef.current = new Gantt(containerRef.current, tasks, {
      view_mode: "Week",
      bar_corner_radius: 4,
      bar_height: 28,
      padding: 18,
      language: "ru",
    });

    return () => {
      ganttRef.current = null;
    };
  }, [activities, dependencies]);

  if (activities.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        Добавьте work packages в WBS — они появятся на диаграмме Ганта.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {overloadedCount > 0 && (
        <p className="text-sm text-accent" role="status">
          Capacity: {overloadedCount} задач с перегруженным исполнителем на
          текущей неделе (подсветка на Gantt).
        </p>
      )}
      <div className="gantt-wrapper overflow-x-auto rounded-xl border border-border bg-surface p-4">
        <div ref={containerRef} />
      </div>
    </div>
  );
}
