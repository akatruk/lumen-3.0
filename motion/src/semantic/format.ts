/** Locale number formatting. The unit is printed only when the payload supplies it. */
export function formatMetric(
  value: number,
  format: "currency" | "percent" | "number",
  locale: string,
  unit?: string,
): string {
  const loc = locale.startsWith("ru") ? "ru-RU" : locale.startsWith("zh") ? "zh-CN" : "en-US";
  const digits = Number.isInteger(value) ? 0 : 1;
  const body = new Intl.NumberFormat(loc, { maximumFractionDigits: digits, minimumFractionDigits: 0 }).format(value);
  if (format === "percent") return `${body}%`;
  if (unit) return `${body} ${unit}`;
  return body;
}
