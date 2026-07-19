import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Locale = "ru" | "en";
export type Currency = "RUB" | "USD" | "EUR";

const messages = {
  ru: {
    dashboard: "Дашборд",
    portfolio: "Портфель",
    projects: "Проекты",
    myTasks: "Мои задачи",
    calendar: "Календарь",
    finance: "Финансы",
    audit: "Аудит",
    administration: "Администрирование",
    settings: "Настройки",
    logout: "Выйти",
    planner: "Ваш личный планировщик",
    dataUpdated: "Данные обновлены",
  },
  en: {
    dashboard: "Dashboard",
    portfolio: "Portfolio",
    projects: "Projects",
    myTasks: "My tasks",
    calendar: "Calendar",
    finance: "Finance",
    audit: "Audit",
    administration: "Administration",
    settings: "Settings",
    logout: "Log out",
    planner: "Your personal project planner",
    dataUpdated: "Data updated",
  },
} as const;

type MessageKey = keyof (typeof messages)["ru"];

type LocaleContextValue = {
  locale: Locale;
  currency: Currency;
  setLocale: (locale: Locale) => void;
  setCurrency: (currency: Currency) => void;
  t: (key: MessageKey) => string;
  formatMoney: (value: number | string) => string;
};

const defaultContext: LocaleContextValue = {
  locale: "ru",
  currency: "RUB",
  setLocale: () => undefined,
  setCurrency: () => undefined,
  t: (key) => messages.ru[key],
  formatMoney: (amount) =>
    new Intl.NumberFormat("ru-RU", {
      style: "currency",
      currency: "RUB",
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    })
      .format(Number(amount))
      .replace(/[\u00A0\u202F]/g, " "),
};

const LocaleContext = createContext<LocaleContextValue>(defaultContext);
const LOCALE_KEY = "fast_plan_locale";
const CURRENCY_KEY = "fast_plan_currency";

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() =>
    localStorage.getItem(LOCALE_KEY) === "en" ? "en" : "ru",
  );
  const [currency, setCurrencyState] = useState<Currency>(() => {
    const saved = localStorage.getItem(CURRENCY_KEY);
    return saved === "USD" || saved === "EUR" ? saved : "RUB";
  });

  const setLocale = useCallback((value: Locale) => {
    setLocaleState(value);
    localStorage.setItem(LOCALE_KEY, value);
    document.documentElement.lang = value;
  }, []);

  const setCurrency = useCallback((value: Currency) => {
    setCurrencyState(value);
    localStorage.setItem(CURRENCY_KEY, value);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      currency,
      setLocale,
      setCurrency,
      t: (key) => messages[locale][key],
      formatMoney: (amount) =>
        new Intl.NumberFormat(locale === "ru" ? "ru-RU" : "en-US", {
          style: "currency",
          currency,
          minimumFractionDigits: 0,
          maximumFractionDigits: 2,
        })
          .format(Number(amount))
          .replace(/[\u00A0\u202F]/g, " "),
    }),
    [locale, currency, setLocale, setCurrency],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  return useContext(LocaleContext);
}
