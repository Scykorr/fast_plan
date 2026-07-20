import type { Currency } from "../context/LocaleContext";

export function convertFromBase(
  amount: number,
  baseCurrency: Currency,
  targetCurrency: Currency,
  rates: Partial<Record<Currency, number>>,
): number {
  if (!Number.isFinite(amount)) {
    return 0;
  }
  if (baseCurrency === targetCurrency) {
    return amount;
  }
  const rate = rates[targetCurrency];
  if (!rate || rate <= 0) {
    return amount;
  }
  return amount / rate;
}
