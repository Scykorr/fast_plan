import type { ProjectLessonsLearned } from "../../api/projects";

type LessonsLearnedEditorProps = {
  lessons: ProjectLessonsLearned;
  onSave: (data: Partial<ProjectLessonsLearned>) => Promise<void>;
};

const fields: { key: keyof ProjectLessonsLearned; label: string }[] = [
  { key: "what_went_well", label: "Что прошло хорошо" },
  { key: "what_went_wrong", label: "Что пошло не так" },
  { key: "recommendations", label: "Рекомендации" },
  { key: "knowledge_to_reuse", label: "Знания для повторного использования" },
];

export function LessonsLearnedEditor({
  lessons,
  onSave,
}: LessonsLearnedEditorProps) {
  const handleBlur = async (
    key: keyof ProjectLessonsLearned,
    value: string,
  ) => {
    if (key === "updated_at") return;
    if (value === lessons[key]) return;
    await onSave({ [key]: value });
  };

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {fields.map((field) => (
        <label key={field.key} className="block text-sm">
          <span className="mb-1 block font-medium text-text">{field.label}</span>
          <textarea
            defaultValue={String(lessons[field.key] ?? "")}
            rows={4}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            onBlur={(event) => void handleBlur(field.key, event.target.value)}
          />
        </label>
      ))}
    </div>
  );
}
