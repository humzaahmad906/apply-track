/** Dates, in the two or three shapes the UI actually needs. */

/**
 * SQLite gives our timestamps back without a timezone, and FastAPI serialises
 * them that way too. They are all UTC, but `new Date("2026-08-05T12:00:00")`
 * reads a bare string as *local* time, which quietly shifts every date by the
 * offset. Stamping the Z back on is the fix.
 */
export function parseUtc(iso: string): Date {
  return new Date(/[Z+]|-\d\d:\d\d$/.test(iso.slice(10)) ? iso : `${iso}Z`);
}

const DAY = 86_400_000;

/** Whole days between two instants, by calendar day rather than by hours. */
function daysBetween(from: Date, to: Date): number {
  const a = Date.UTC(from.getFullYear(), from.getMonth(), from.getDate());
  const b = Date.UTC(to.getFullYear(), to.getMonth(), to.getDate());
  return Math.round((b - a) / DAY);
}

export function shortDate(iso: string | null): string {
  if (!iso) return "—";
  return parseUtc(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
  });
}

export function longDate(iso: string | null): string {
  if (!iso) return "—";
  return parseUtc(iso).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** "today", "in 3 days", "12 days ago" — the phrasing the queue uses. */
export function relative(iso: string | null): string {
  if (!iso) return "";
  const days = daysBetween(new Date(), parseUtc(iso));
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  if (days === -1) return "yesterday";
  return days > 0 ? `in ${days} days` : `${-days} days ago`;
}

export function daysAgo(iso: string | null): number {
  if (!iso) return 0;
  return Math.max(0, -daysBetween(new Date(), parseUtc(iso)));
}

/** Value for an <input type="datetime-local">, which wants local wall time. */
export function toDateTimeInput(iso: string | null): string {
  if (!iso) return "";
  const d = parseUtc(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

/** The reverse: a datetime-local value back into an absolute instant. */
export function fromDateTimeInput(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

export function inDays(n: number): string {
  return new Date(Date.now() + n * DAY).toISOString();
}
