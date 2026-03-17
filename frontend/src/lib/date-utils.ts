/**
 * Date/time utilities that consistently use the browser's local timezone.
 * Avoids mixing UTC (toISOString) with local (toTimeString) which causes
 * date shifts for events between midnight and UTC offset hours.
 */

export function toLocalDateStr(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function toLocalTimeStr(d: Date): string {
  const hours = String(d.getHours()).padStart(2, "0");
  const mins = String(d.getMinutes()).padStart(2, "0");
  return `${hours}:${mins}`;
}

export function getTimezoneOffsetStr(): string {
  const offsetMin = -new Date().getTimezoneOffset();
  const sign = offsetMin >= 0 ? "+" : "-";
  const h = String(Math.floor(Math.abs(offsetMin) / 60)).padStart(2, "0");
  const m = String(Math.abs(offsetMin) % 60).padStart(2, "0");
  return `${sign}${h}:${m}`;
}

export function buildISOWithTZ(date: string, time: string): string {
  const tz = getTimezoneOffsetStr();
  return `${date}T${time}:00${tz}`;
}
