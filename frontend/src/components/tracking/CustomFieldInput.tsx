import type { ReactNode } from "react";

import type { CustomField } from "../../api/tracking";
import {
  CUSTOM_FIELD_FORMATS,
  parseLinkListValue,
  serializeLinkListValue,
} from "./fieldFormats";

type CustomFieldInputProps = {
  field: CustomField;
  value: string;
  onChange: (value: string) => void;
};

export function CustomFieldInput({ field, value, onChange }: CustomFieldInputProps) {
  const label = (
    <span className="text-text-muted">
      {field.name}
      {field.is_required ? " *" : ""}
    </span>
  );

  if (field.field_format === "text") {
    return (
      <label className="block text-sm">
        {label}
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          rows={3}
          className="mt-1 w-full rounded-lg border border-border px-3 py-2"
        />
      </label>
    );
  }

  if (field.field_format === "list") {
    const options = field.enumerations.filter((item) => !item.parent_id);
    return (
      <label className="block text-sm">
        {label}
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="mt-1 w-full rounded-lg border border-border px-3 py-2"
        >
          <option value="">—</option>
          {options.map((item) => (
            <option key={item.id} value={item.name}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
    );
  }

  if (field.field_format === "link_list") {
    return (
      <LinkListInput field={field} value={value} onChange={onChange} label={label} />
    );
  }

  if (field.field_format === "bool") {
    return (
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={value === "true" || value === "1"}
          onChange={(event) => onChange(event.target.checked ? "true" : "false")}
        />
        {field.name}
      </label>
    );
  }

  if (field.field_format === "percent") {
    return (
      <label className="block text-sm">
        {label}
        <input
          type="number"
          min={0}
          max={100}
          step={1}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="mt-1 w-full rounded-lg border border-border px-3 py-2"
        />
      </label>
    );
  }

  const inputType = getInputType(field.field_format);

  return (
    <label className="block text-sm">
      {label}
      <input
        type={inputType}
        value={value}
        step={field.field_format === "float" ? "any" : field.field_format === "int" ? 1 : undefined}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-lg border border-border px-3 py-2"
      />
    </label>
  );
}

function LinkListInput({
  field,
  value,
  onChange,
  label,
}: {
  field: CustomField;
  value: string;
  onChange: (value: string) => void;
  label: ReactNode;
}) {
  const parsed = parseLinkListValue(value);
  const parents = field.enumerations.filter((item) => !item.parent_id);

  return (
    <div className="space-y-2 text-sm">
      {label}
      <select
        value={parsed?.parent_id ?? ""}
        onChange={(event) => {
          const parentId = Number(event.target.value);
          if (!parentId) {
            onChange("");
            return;
          }
          onChange(serializeLinkListValue({ parent_id: parentId, child_id: 0 }));
        }}
        className="w-full rounded-lg border border-border px-3 py-2"
      >
        <option value="">Выберите категорию</option>
        {parents.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </select>
      <select
        value={parsed?.child_id ?? ""}
        disabled={!parsed?.parent_id}
        onChange={(event) => {
          const childId = Number(event.target.value);
          if (!parsed?.parent_id || !childId) {
            return;
          }
          onChange(
            serializeLinkListValue({ parent_id: parsed.parent_id, child_id: childId }),
          );
        }}
        className="w-full rounded-lg border border-border px-3 py-2 disabled:bg-cream"
      >
        <option value="">Выберите значение</option>
        {field.enumerations
          .filter((item) => item.parent_id === parsed?.parent_id)
          .map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
      </select>
      {parsed?.parent_id && field.enumerations.filter((item) => item.parent_id === parsed.parent_id).length === 0 && (
        <p className="text-xs text-text-muted">Для категории нет дочерних значений</p>
      )}
    </div>
  );
}

function getInputType(format: string): string {
  switch (format) {
    case "int":
    case "float":
      return "number";
    case "date":
      return "date";
    case "datetime":
      return "datetime-local";
    case "email":
      return "email";
    case "url":
      return "url";
    default:
      return "text";
  }
}

export { CUSTOM_FIELD_FORMATS };
