import { ApiError } from "./client";

function formatFieldErrors(data: Record<string, unknown>): string[] {
  const messages: string[] = [];

  for (const [field, value] of Object.entries(data)) {
    if (field === "detail" || field === "non_field_errors") {
      continue;
    }
    if (Array.isArray(value)) {
      value.forEach((message) => {
        if (typeof message === "string") {
          messages.push(`${field}: ${message}`);
        }
      });
    } else if (typeof value === "string") {
      messages.push(`${field}: ${value}`);
    }
  }

  return messages;
}

export function parseApiError(error: unknown, fallback = "Произошла ошибка"): string {
  if (error instanceof ApiError) {
    const data = error.data;

    if (typeof data.detail === "string") {
      return data.detail;
    }

    if (Array.isArray(data.non_field_errors)) {
      return data.non_field_errors.join(" ");
    }

    const fieldErrors = formatFieldErrors(data);
    if (fieldErrors.length > 0) {
      return fieldErrors.join(" ");
    }

    if (error.status === 401) {
      return "Неверный email или пароль";
    }

    if (error.status >= 500) {
      return "Сервер временно недоступен. Попробуйте позже.";
    }
  }

  if (error instanceof TypeError) {
    return "Нет соединения с сервером";
  }

  return fallback;
}
