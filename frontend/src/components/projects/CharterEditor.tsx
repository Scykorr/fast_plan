import type { ProjectCharter } from "../../api/projects";

type CharterEditorProps = {
  charter: ProjectCharter;
  onSave: (data: Partial<ProjectCharter>) => Promise<void>;
};

const fields: { key: keyof ProjectCharter; label: string }[] = [
  { key: "goals", label: "Цели проекта" },
  { key: "success_criteria", label: "Критерии успеха" },
  { key: "constraints", label: "Ограничения" },
  { key: "assumptions", label: "Допущения" },
];

export function CharterEditor({ charter, onSave }: CharterEditorProps) {
  const handleBlur = async (
    key: keyof ProjectCharter,
    value: string,
  ) => {
    if (value === charter[key]) {
      return;
    }
    await onSave({ [key]: value });
  };

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {fields.map((field) => (
        <label key={field.key} className="block text-sm">
          <span className="mb-1 block font-medium text-text">{field.label}</span>
          <textarea
            defaultValue={charter[field.key]}
            rows={4}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            onBlur={(event) => void handleBlur(field.key, event.target.value)}
          />
        </label>
      ))}
    </div>
  );
}
