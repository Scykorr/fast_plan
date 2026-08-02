/**
 * Glossary of foreign abbreviations / product terms → Russian hints.
 * Keys are matched case-insensitively; prefer longest match first in GlossaryText.
 */

export type GlossaryEntry = {
  /** Canonical display form (optional) */
  label?: string;
  /** Full expansion in Russian / Latin if useful */
  full?: string;
  /** Short Russian explanation shown in the popup */
  hint: string;
};

/** Map of lowercase key → entry. Include common aliases. */
export const GLOSSARY: Record<string, GlossaryEntry> = {
  wbs: {
    label: "WBS",
    full: "Work Breakdown Structure",
    hint: "иерархическая структура работ проекта",
  },
  gantt: {
    label: "Gantt",
    hint: "диаграмма Ганта — сроки задач на шкале времени",
  },
  pert: {
    label: "PERT",
    full: "Program Evaluation and Review Technique",
    hint: "сетевой анализ сроков и вероятностная оценка длительности",
  },
  cpm: {
    label: "CPM",
    full: "Critical Path Method",
    hint: "метод критического пути — самые длинные цепочки задач",
  },
  evm: {
    label: "EVM",
    full: "Earned Value Management",
    hint: "управление освоенным объёмом (план/факт стоимости и сроков)",
  },
  spi: {
    label: "SPI",
    full: "Schedule Performance Index",
    hint: "индекс выполнения сроков (>1 — опережение)",
  },
  cpi: {
    label: "CPI",
    full: "Cost Performance Index",
    hint: "индекс выполнения бюджета (>1 — экономия)",
  },
  raci: {
    label: "RACI",
    hint: "матрица ролей: Responsible / Accountable / Consulted / Informed",
  },
  kanban: {
    label: "Kanban",
    hint: "доска задач по колонкам статуса (карточки)",
  },
  baseline: {
    label: "Baseline",
    hint: "зафиксированный снимок плана для сравнения с фактом",
  },
  capacity: {
    label: "Capacity",
    hint: "доступная загрузка людей (часы в неделю)",
  },
  workspace: {
    label: "Workspace",
    hint: "рабочее пространство команды (общие проекты и настройки)",
  },
  bpmn: {
    label: "BPMN",
    full: "Business Process Model and Notation",
    hint: "стандартная нотация схем бизнес-процессов",
  },
  dmn: {
    label: "DMN",
    full: "Decision Model and Notation",
    hint: "таблицы решений (правила «если → то»)",
  },
  cmmn: {
    label: "CMMN",
    full: "Case Management Model and Notation",
    hint: "управление кейсами с гибким порядком шагов",
  },
  smtp: {
    label: "SMTP",
    full: "Simple Mail Transfer Protocol",
    hint: "протокол отправки электронной почты",
  },
  sla: {
    label: "SLA",
    full: "Service Level Agreement",
    hint: "согласованный уровень сервиса / срок реакции",
  },
  arr: {
    label: "ARR",
    full: "Annual Recurring Revenue",
    hint: "годовая регулярная выручка по подпискам/договорам",
  },
  sku: {
    label: "SKU",
    full: "Stock Keeping Unit",
    hint: "артикул / складская позиция номенклатуры",
  },
  pwa: {
    label: "PWA",
    full: "Progressive Web App",
    hint: "веб-приложение с установкой и офлайн-режимом",
  },
  sse: {
    label: "SSE",
    full: "Server-Sent Events",
    hint: "поток событий с сервера в браузер в реальном времени",
  },
  api: {
    label: "API",
    full: "Application Programming Interface",
    hint: "программный интерфейс для обмена данными",
  },
  pdf: {
    label: "PDF",
    hint: "формат документа для печати и обмена",
  },
  csv: {
    label: "CSV",
    hint: "табличные данные в текстовом файле через разделители",
  },
  xlsx: {
    label: "XLSX",
    hint: "файл Excel (таблица)",
  },
  ics: {
    label: "ICS",
    hint: "формат календаря (iCalendar) для вех и дедлайнов",
  },
  jwt: {
    label: "JWT",
    full: "JSON Web Token",
    hint: "токен авторизации для сессии API",
  },
  sso: {
    label: "SSO",
    full: "Single Sign-On",
    hint: "единый вход через внешний провайдер (например Microsoft)",
  },
  "2fa": {
    label: "2FA",
    full: "Two-Factor Authentication",
    hint: "двухфакторная аутентификация",
  },
  oauth: {
    label: "OAuth",
    hint: "стандарт делегированного доступа (Google/Outlook и др.)",
  },
  hmac: {
    label: "HMAC",
    hint: "подпись запросов общим секретом (webhooks)",
  },
  webhook: {
    label: "Webhook",
    hint: "исходящее HTTP-уведомление о событии во внешнюю систему",
  },
  webhooks: {
    label: "Webhooks",
    hint: "исходящие HTTP-уведомления о событиях во внешние системы",
  },
  adapters: {
    label: "Adapters",
    hint: "каталог операций ServiceTask (интеграции процесса)",
  },
  ops: {
    label: "Ops",
    hint: "операционная сводка: застрявшие / стареющие задачи и SLA",
  },
  mining: {
    label: "Mining",
    hint: "process mining — анализ фактических путей выполнения",
  },
  pmbok: {
    label: "PMBOK",
    hint: "свод знаний по управлению проектами (стандарт PMI)",
  },
  crm: {
    label: "CRM",
    full: "Customer Relationship Management",
    hint: "учёт клиентов, сделок и коммуникаций",
  },
  fx: {
    label: "FX",
    full: "Foreign Exchange",
    hint: "курсы валют и конвертация",
  },
  fs: {
    label: "FS",
    full: "Finish-to-Start",
    hint: "связь: следующая задача стартует после окончания предыдущей",
  },
  ss: {
    label: "SS",
    full: "Start-to-Start",
    hint: "связь: задачи стартуют согласованно",
  },
  ff: {
    label: "FF",
    full: "Finish-to-Finish",
    hint: "связь: задачи заканчиваются согласованно",
  },
  sf: {
    label: "SF",
    full: "Start-to-Finish",
    hint: "связь: окончание зависит от старта предшественника",
  },
  llm: {
    label: "LLM",
    full: "Large Language Model",
    hint: "большая языковая модель (AI-черновики)",
  },
  ai: {
    label: "AI",
    hint: "искусственный интеллект (черновики и подсказки)",
  },
  uuid: {
    label: "UUID",
    hint: "универсальный уникальный идентификатор",
  },
  url: {
    label: "URL",
    hint: "адрес страницы или API в интернете",
  },
};

export function lookupGlossary(raw: string): GlossaryEntry | null {
  const key = raw.trim().toLowerCase();
  if (!key) return null;
  return GLOSSARY[key] ?? null;
}

/** Terms sorted longest-first for regex matching. */
export function glossaryTermKeys(): string[] {
  return Object.keys(GLOSSARY).sort((a, b) => b.length - a.length);
}

export function formatGlossaryPopup(entry: GlossaryEntry): string {
  if (entry.full) {
    return `${entry.full} — ${entry.hint}`;
  }
  return entry.hint;
}
