import type { WorkspaceMember } from "../../api/workspace";

type AssigneeSelectProps = {
  members: WorkspaceMember[];
  value: number | null | "";
  onChange: (userId: number | null) => void;
  className?: string;
  label?: string;
  emptyLabel?: string;
  disabled?: boolean;
};

export function AssigneeSelect({
  members,
  value,
  onChange,
  className = "mt-1 w-full rounded-lg border border-border bg-cream px-3 py-2 text-sm",
  label,
  emptyLabel = "Не назначен",
  disabled = false,
}: AssigneeSelectProps) {
  const select = (
    <select
      className={className}
      disabled={disabled}
      value={value === null || value === "" ? "" : String(value)}
      onChange={(event) => {
        const raw = event.target.value;
        onChange(raw ? Number(raw) : null);
      }}
    >
      <option value="">{emptyLabel}</option>
      {members.map((m) => (
        <option key={m.user_id} value={m.user_id}>
          {m.email || m.username}
        </option>
      ))}
    </select>
  );

  if (!label) {
    return select;
  }

  return (
    <label className="block text-sm">
      <span className="text-text-muted">{label}</span>
      {select}
    </label>
  );
}
