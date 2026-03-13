import { describe, it, expect } from "vitest";
import {
  getCoverStyle,
  getThemeCoverStyle,
  getThemeById,
  getThemeForEvent,
  EVENT_THEMES,
} from "../themes";

describe("getCoverStyle", () => {
  const baseEvent = { id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" };

  it("returns theme gradient when no cover_image_url", () => {
    const style = getCoverStyle(baseEvent);
    expect(style.background).toBeDefined();
    expect(String(style.background)).toContain("linear-gradient");
  });

  it("returns image + theme gradient fallback when cover_image_url is set", () => {
    const event = { ...baseEvent, cover_image_url: "https://example.com/img.jpg" };
    const style = getCoverStyle(event);
    const bg = String(style.background);
    expect(bg).toContain('url("https://example.com/img.jpg")');
    expect(bg).toContain("center/cover no-repeat");
    expect(bg).toContain("linear-gradient");
  });

  it("uses preset theme when theme.preset is set", () => {
    const event = { ...baseEvent, theme: { preset: "sunset" } };
    const style = getCoverStyle(event);
    const sunsetTheme = getThemeById("sunset")!;
    expect(String(style.background)).toContain(sunsetTheme.gradient);
  });

  it("falls back to hash-based theme when no theme preset", () => {
    const style = getCoverStyle(baseEvent);
    expect(style.background).toBeDefined();
  });

  it("includes theme gradient as fallback layer behind cover image", () => {
    const event = {
      ...baseEvent,
      cover_image_url: "https://cdn.example.com/broken.jpg",
      theme: { preset: "ocean" },
    };
    const style = getCoverStyle(event);
    const bg = String(style.background);
    const oceanTheme = getThemeById("ocean")!;
    expect(bg).toContain(oceanTheme.gradient);
    expect(bg).toContain("broken.jpg");
  });
});

describe("getThemeCoverStyle", () => {
  it("includes pattern and gradient when theme has pattern", () => {
    const aurora = getThemeById("aurora")!;
    const style = getThemeCoverStyle(aurora);
    expect(String(style.background)).toContain("data:image/svg+xml");
    expect(String(style.background)).toContain(aurora.gradient);
  });

  it("returns only gradient when theme has no pattern", () => {
    const noPatternTheme = { ...EVENT_THEMES[0], pattern: undefined };
    const style = getThemeCoverStyle(noPatternTheme);
    expect(style.background).toBe(noPatternTheme.gradient);
  });
});

describe("getThemeForEvent", () => {
  it("returns matching theme for preset", () => {
    const theme = getThemeForEvent({ id: "test-id", theme: { preset: "fire" } });
    expect(theme.id).toBe("fire");
  });

  it("falls back to hash-based theme for unknown preset", () => {
    const theme = getThemeForEvent({ id: "abcdef01-2345-6789-abcd-ef0123456789", theme: { preset: "nonexistent" } });
    expect(EVENT_THEMES).toContainEqual(theme);
  });

  it("falls back to hash-based theme when no theme set", () => {
    const theme = getThemeForEvent({ id: "abcdef01-2345-6789-abcd-ef0123456789" });
    expect(EVENT_THEMES).toContainEqual(theme);
  });
});
