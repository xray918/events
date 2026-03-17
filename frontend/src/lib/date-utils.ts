/**
 * Date/time utilities — always operate in the event's timezone, not the browser's.
 *
 * Core principle: the time user sees and enters IS the event location's time,
 * regardless of where the editor is located.
 */

const DEFAULT_EVENT_TZ = "Asia/Shanghai";

/** Extract YYYY-MM-DD in the event's timezone. */
export function toTZDateStr(d: Date, tz: string = DEFAULT_EVENT_TZ): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(d);
  const get = (t: string) => parts.find((p) => p.type === t)?.value || "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}

/** Extract HH:MM in the event's timezone. */
export function toTZTimeStr(d: Date, tz: string = DEFAULT_EVENT_TZ): string {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: tz,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(d);
  const get = (t: string) => parts.find((p) => p.type === t)?.value || "";
  return `${get("hour")}:${get("minute")}`;
}

/** Get UTC offset string (e.g. "+08:00") for a timezone at a given instant. */
export function getTZOffsetStr(
  d: Date,
  tz: string = DEFAULT_EVENT_TZ,
): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    timeZoneName: "longOffset",
  }).formatToParts(d);
  const tzName = parts.find((p) => p.type === "timeZoneName")?.value || "";
  if (tzName === "GMT") return "+00:00";
  const m = tzName.match(/GMT([+-]\d{2}:\d{2})/);
  return m ? m[1] : "+00:00";
}

/**
 * Build an ISO datetime string in the event's timezone.
 * E.g. buildISOInTZ("2026-03-21", "18:00", "Asia/Shanghai") → "2026-03-21T18:00:00+08:00"
 */
export function buildISOInTZ(
  date: string,
  time: string,
  tz: string = DEFAULT_EVENT_TZ,
): string {
  const offset = getTZOffsetStr(new Date(`${date}T${time}:00`), tz);
  return `${date}T${time}:00${offset}`;
}
