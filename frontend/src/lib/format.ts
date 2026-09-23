// Presentation helpers. Numbers stay concrete and tabular (ui-spec §8).

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** "2 min ago", "3h ago", "4d ago". Never "a moment ago". */
export function relativeTime(iso: string, now = Date.now()): string {
  const elapsed = Math.max(0, now - new Date(iso).getTime());
  if (elapsed < MINUTE) return "just now";
  if (elapsed < HOUR) return `${Math.floor(elapsed / MINUTE)} min ago`;
  if (elapsed < DAY) return `${Math.floor(elapsed / HOUR)}h ago`;
  return `${Math.floor(elapsed / DAY)}d ago`;
}

/** 48200 → "48.2K". Keeps one decimal so ranking differences stay visible. */
export function compactNumber(value: number): string {
  if (value < 1_000) return String(value);
  if (value < 1_000_000) return `${(value / 1_000).toFixed(1)}K`;
  return `${(value / 1_000_000).toFixed(1)}M`;
}

/** "▲142%", "▼12%", "0%". The arrow carries the direction, not the colour. */
export function signedPercent(value: number): string {
  const rounded = Math.round(Math.abs(value) * 10) / 10;
  if (value > 0) return `▲${rounded}%`;
  if (value < 0) return `▼${rounded}%`;
  return "0%";
}

const CURRENCY_SYMBOLS: Record<string, string> = { AUD: "$", USD: "$", EUR: "€", GBP: "£" };

/** "$2,500". The currency code is shown separately where it matters. */
export function money(amount: number, currency: string): string {
  return `${CURRENCY_SYMBOLS[currency] ?? ""}${amount.toLocaleString("en-AU")}`;
}

/** Initials for an influencer monogram. No avatar images (ui-spec §3). */
export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/** Hostname plus a clipped path, for the link line on an activity card. */
export function displayUrl(url: string, maxLength = 34): string {
  const stripped = url.replace(/^https?:\/\//, "").replace(/^www\./, "");
  return stripped.length <= maxLength ? stripped : `${stripped.slice(0, maxLength)}…`;
}
