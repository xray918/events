import { describe, it, expect } from "vitest";
import {
  toTZDateStr,
  toTZTimeStr,
  getTZOffsetStr,
  buildISOInTZ,
} from "../date-utils";

describe("toTZDateStr", () => {
  it("extracts date in Asia/Shanghai timezone", () => {
    // 2026-03-21T10:00:00Z = 2026-03-21T18:00:00+08:00
    const d = new Date("2026-03-21T10:00:00Z");
    expect(toTZDateStr(d, "Asia/Shanghai")).toBe("2026-03-21");
  });

  it("handles date boundary — UTC previous day, Shanghai same day", () => {
    // 2026-03-21T20:00:00Z = 2026-03-22T04:00:00+08:00
    const d = new Date("2026-03-21T20:00:00Z");
    expect(toTZDateStr(d, "Asia/Shanghai")).toBe("2026-03-22");
  });

  it("NZ user sees Shanghai date, not NZ date", () => {
    // 2026-03-21T10:00:00Z = 18:00 Shanghai = 23:00 NZ (NZDT, +13)
    const d = new Date("2026-03-21T10:00:00Z");
    expect(toTZDateStr(d, "Asia/Shanghai")).toBe("2026-03-21");
  });
});

describe("toTZTimeStr", () => {
  it("extracts time in Asia/Shanghai timezone", () => {
    const d = new Date("2026-03-21T10:00:00Z");
    expect(toTZTimeStr(d, "Asia/Shanghai")).toBe("18:00");
  });

  it("extracts time in UTC", () => {
    const d = new Date("2026-03-21T10:00:00Z");
    expect(toTZTimeStr(d, "UTC")).toBe("10:00");
  });

  it("NZ user still sees Shanghai time, not NZ time", () => {
    // 10:00 UTC = 18:00 Shanghai — should show 18:00, not 23:00 (NZ)
    const d = new Date("2026-03-21T10:00:00Z");
    expect(toTZTimeStr(d, "Asia/Shanghai")).toBe("18:00");
  });

  it("handles early morning correctly", () => {
    // 2026-03-21T17:00:00Z = 2026-03-22T01:00:00+08:00
    const d = new Date("2026-03-21T17:00:00Z");
    expect(toTZTimeStr(d, "Asia/Shanghai")).toBe("01:00");
    expect(toTZDateStr(d, "Asia/Shanghai")).toBe("2026-03-22");
  });
});

describe("getTZOffsetStr", () => {
  it("returns +08:00 for Asia/Shanghai", () => {
    const d = new Date("2026-03-21T10:00:00Z");
    expect(getTZOffsetStr(d, "Asia/Shanghai")).toBe("+08:00");
  });

  it("returns +00:00 for UTC", () => {
    const d = new Date("2026-03-21T10:00:00Z");
    expect(getTZOffsetStr(d, "UTC")).toBe("+00:00");
  });
});

describe("buildISOInTZ", () => {
  it("builds ISO string with Shanghai offset", () => {
    const result = buildISOInTZ("2026-03-21", "18:00", "Asia/Shanghai");
    expect(result).toBe("2026-03-21T18:00:00+08:00");
  });

  it("builds ISO string with UTC offset", () => {
    const result = buildISOInTZ("2026-03-21", "10:00", "UTC");
    expect(result).toBe("2026-03-21T10:00:00+00:00");
  });

  it("defaults to Asia/Shanghai when no timezone given", () => {
    const result = buildISOInTZ("2026-03-21", "18:00");
    expect(result).toBe("2026-03-21T18:00:00+08:00");
  });

  it("round-trips correctly — load then save preserves UTC instant", () => {
    const originalUTC = "2026-03-21T10:00:00Z";
    const d = new Date(originalUTC);
    const tz = "Asia/Shanghai";

    const dateStr = toTZDateStr(d, tz);
    const timeStr = toTZTimeStr(d, tz);
    const rebuilt = buildISOInTZ(dateStr, timeStr, tz);

    expect(new Date(rebuilt).getTime()).toBe(d.getTime());
  });

  it("round-trips early morning in Shanghai correctly", () => {
    // 01:00 Shanghai = previous day 17:00 UTC
    const originalUTC = "2026-03-21T17:00:00Z";
    const d = new Date(originalUTC);
    const tz = "Asia/Shanghai";

    const dateStr = toTZDateStr(d, tz);
    const timeStr = toTZTimeStr(d, tz);
    expect(dateStr).toBe("2026-03-22");
    expect(timeStr).toBe("01:00");

    const rebuilt = buildISOInTZ(dateStr, timeStr, tz);
    expect(new Date(rebuilt).getTime()).toBe(d.getTime());
  });

  it("cross-timezone edit: NZ user editing Shanghai event preserves time", () => {
    // Shanghai event at 18:00 (10:00 UTC)
    const d = new Date("2026-03-21T10:00:00Z");
    const tz = "Asia/Shanghai";

    // Both NZ and China users see the same Shanghai time
    const dateStr = toTZDateStr(d, tz);
    const timeStr = toTZTimeStr(d, tz);
    expect(dateStr).toBe("2026-03-21");
    expect(timeStr).toBe("18:00");

    // Saving produces the same UTC instant
    const rebuilt = buildISOInTZ(dateStr, timeStr, tz);
    expect(rebuilt).toBe("2026-03-21T18:00:00+08:00");
    expect(new Date(rebuilt).getTime()).toBe(d.getTime());
  });
});
