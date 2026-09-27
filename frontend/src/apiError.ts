/** FastAPI validation errors are a list. Named codes inside them stay visible. */

export function apiErrorCode(data: unknown): string {
  if (!data || typeof data !== "object" || !("detail" in data)) return "request_failed";
  const detail = (data as { detail: unknown }).detail;
  if (typeof detail === "string" && detail) return detail;
  if (!Array.isArray(detail)) return "request_failed";
  const text = detail
    .map((item) => (item && typeof item === "object" && "msg" in item ? String((item as { msg: unknown }).msg) : ""))
    .join("\n");
  const named = text.match(/\b(invalid_date|invalid_url)\b/);
  return named ? named[1] : "request_failed";
}
