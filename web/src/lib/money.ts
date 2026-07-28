export type MoneyCurrency = "RUB" | "EUR" | "USD" | "KZT" | "BYN" | "RSD";

export function formatMoney(value: number, currency: string = "RUB"): string {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: currency as MoneyCurrency,
    maximumFractionDigits: 2,
  }).format(value);
}
