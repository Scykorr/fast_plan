export type CustomFieldFormat =
  | "string"
  | "text"
  | "int"
  | "float"
  | "percent"
  | "bool"
  | "date"
  | "datetime"
  | "list"
  | "link_list"
  | "user"
  | "url"
  | "email";

export type CustomFieldFormatMeta = {
  value: CustomFieldFormat;
  label: string;
  description: string;
  hasEnumerations: boolean;
  isLinkedList?: boolean;
};

export const CUSTOM_FIELD_FORMATS: CustomFieldFormatMeta[] = [
  {
    value: "string",
    label: "Строка",
    description: "Короткий однострочный текст",
    hasEnumerations: false,
  },
  {
    value: "text",
    label: "Текст",
    description: "Многострочный текст",
    hasEnumerations: false,
  },
  {
    value: "int",
    label: "Целое число",
    description: "Только целые значения",
    hasEnumerations: false,
  },
  {
    value: "float",
    label: "Вещественное число",
    description: "Числа с дробной частью",
    hasEnumerations: false,
  },
  {
    value: "percent",
    label: "Процент",
    description: "Значение от 0 до 100",
    hasEnumerations: false,
  },
  {
    value: "bool",
    label: "Флаг (да/нет)",
    description: "Логическое значение",
    hasEnumerations: false,
  },
  {
    value: "date",
    label: "Дата",
    description: "Календарная дата",
    hasEnumerations: false,
  },
  {
    value: "datetime",
    label: "Дата и время",
    description: "Дата с указанием времени",
    hasEnumerations: false,
  },
  {
    value: "list",
    label: "Выпадающий список",
    description: "Один вариант из заданных значений",
    hasEnumerations: true,
  },
  {
    value: "link_list",
    label: "Связанные списки",
    description: "Два связанных списка (категория → значение)",
    hasEnumerations: true,
    isLinkedList: true,
  },
  {
    value: "user",
    label: "Пользователь",
    description: "ID пользователя workspace",
    hasEnumerations: false,
  },
  {
    value: "url",
    label: "Ссылка (URL)",
    description: "Веб-адрес",
    hasEnumerations: false,
  },
  {
    value: "email",
    label: "Email",
    description: "Адрес электронной почты",
    hasEnumerations: false,
  },
];

export function getFieldFormatMeta(format: string): CustomFieldFormatMeta | undefined {
  return CUSTOM_FIELD_FORMATS.find((item) => item.value === format);
}

export function formatHasEnumerations(format: string): boolean {
  return Boolean(getFieldFormatMeta(format)?.hasEnumerations);
}

export type LinkListValue = {
  parent_id: number;
  child_id: number;
};

export function parseLinkListValue(raw: string): LinkListValue | null {
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as LinkListValue;
    if (parsed.parent_id && parsed.child_id) {
      return parsed;
    }
  } catch {
    return null;
  }
  return null;
}

export function serializeLinkListValue(value: LinkListValue): string {
  return JSON.stringify(value);
}
