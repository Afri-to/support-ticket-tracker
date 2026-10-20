// Small, pure formatting helpers (unit-tested in format.test.ts).

const DAY_MS = 24 * 60 * 60 * 1000;

/** "2026-07-06" -> Date at local midnight (avoids the UTC-shift bug of new Date("2026-07-06")). */
export function parseDay(day: string): Date {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function toDay(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** The Sunday that ends the week starting on `weekStart`. */
export function weekEnd(weekStart: string): string {
  return toDay(new Date(parseDay(weekStart).getTime() + 6 * DAY_MS));
}

const short = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" });

/** "Jul 6" - used on chart axes. */
export function shortDay(day: string): string {
  return short.format(parseDay(day));
}

/** "Jul 6 – Jul 12" - used in the week picker and tooltips. */
export function weekLabel(weekStart: string): string {
  return `${shortDay(weekStart)} – ${shortDay(weekEnd(weekStart))}`;
}

const integer = new Intl.NumberFormat("en-US");

export function count(n: number): string {
  return integer.format(n);
}

/** Hours as "4.5 h"; days for long spans ("2.1 days"); "–" when unknown. */
export function hours(value: string | number | null): string {
  if (value === null || value === undefined) return "–";
  const h = Number(value);
  if (h >= 48) return `${(h / 24).toFixed(1)} days`;
  return `${h.toFixed(1)} h`;
}

const stamp = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZone: "UTC",
});

/** Ticket timestamps are shown in UTC, the time zone the data was imported in. */
export function dateTime(iso: string): string {
  return stamp.format(new Date(iso));
}
