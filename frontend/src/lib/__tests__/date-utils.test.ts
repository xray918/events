import { describe, it, expect } from "vitest";
import {
  toLocalDateStr,
  toLocalTimeStr,
  getTimezoneOffsetStr,
  buildISOWithTZ,
} from "../date-utils";

describe("toLocalDateStr", () => {
  it("returns local date in YYYY-MM-DD format", () => {
    const d = new Date(2026, 2, 21, 18, 0); // March 21, 2026 18:00 local
    expect(toLocalDateStr(d)).toBe("2026-03-21");
  });

  it("pads single-digit month and day", () => {
    const d = new Date(2026, 0, 5, 1, 0); // Jan 5, 2026 01:00 local
    expect(toLocalDateStr(d)).toBe("2026-01-05");
  });

  it("uses local date, not UTC date (critical for early morning times)", () => {
    // Simulate: 2026-03-22T01:00:00+08:00 = 2026-03-21T17:00:00Z
    // UTC date is March 21, but local date (UTC+8) is March 22
    const d = new Date("2026-03-21T17:00:00Z");
    const localDate = toLocalDateStr(d);
    const localDay = d.getDate();
    expect(localDate).toContain(String(localDay).padStart(2, "0"));
  });
});

describe("toLocalTimeStr", () => {
  it("returns local time in HH:MM format", () => {
    const d = new Date(2026, 2, 21, 18, 30);
    expect(toLocalTimeStr(d)).toBe("18:30");
  });

  it("pads single-digit hours and minutes", () => {
    const d = new Date(2026, 2, 21, 1, 5);
    expect(toLocalTimeStr(d)).toBe("01:05");
  });

  it("handles midnight", () => {
    const d = new Date(2026, 2, 21, 0, 0);
    expect(toLocalTimeStr(d)).toBe("00:00");
  });
});

describe("getTimezoneOffsetStr", () => {
  it("returns a valid timezone offset string", () => {
    const tz = getTimezoneOffsetStr();
    expect(tz).toMatch(/^[+-]\d{2}:\d{2}$/);
  });
});

describe("buildISOWithTZ", () => {
  it("combines date and time with timezone offset", () => {
    const result = buildISOWithTZ("2026-03-21", "18:00");
    const tz = getTimezoneOffsetStr();
    expect(result).toBe(`2026-03-21T18:00:00${tz}`);
  });

  it("produces a valid ISO datetime parseable by Date", () => {
    const result = buildISOWithTZ("2026-03-21", "18:00");
    const parsed = new Date(result);
    expect(parsed.getTime()).not.toBeNaN();
  });

  it("round-trips correctly: build → parse → extract → build", () => {
    const original = buildISOWithTZ("2026-03-21", "19:30");
    const parsed = new Date(original);
    const dateStr = toLocalDateStr(parsed);
    const timeStr = toLocalTimeStr(parsed);
    const rebuilt = buildISOWithTZ(dateStr, timeStr);
    expect(new Date(rebuilt).getTime()).toBe(parsed.getTime());
  });

  it("round-trips early morning times correctly", () => {
    const original = buildISOWithTZ("2026-03-22", "01:00");
    const parsed = new Date(original);
    const dateStr = toLocalDateStr(parsed);
    const timeStr = toLocalTimeStr(parsed);
    expect(dateStr).toBe("2026-03-22");
    expect(timeStr).toBe("01:00");
    const rebuilt = buildISOWithTZ(dateStr, timeStr);
    expect(new Date(rebuilt).getTime()).toBe(parsed.getTime());
  });
});
