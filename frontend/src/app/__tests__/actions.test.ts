import { describe, it, expect, vi, beforeEach } from "vitest";

const mockRevalidatePath = vi.fn();

vi.mock("next/cache", () => ({
  revalidatePath: (...args: unknown[]) => mockRevalidatePath(...args),
}));

import { revalidateEventPage, revalidateEventList } from "../actions";

describe("revalidateEventPage", () => {
  beforeEach(() => {
    mockRevalidatePath.mockClear();
  });

  it("calls revalidatePath with the correct event slug path", async () => {
    await revalidateEventPage("my-event-slug");
    expect(mockRevalidatePath).toHaveBeenCalledWith("/e/my-event-slug");
    expect(mockRevalidatePath).toHaveBeenCalledTimes(1);
  });

  it("handles slugs with special characters", async () => {
    await revalidateEventPage("openclaw-wuhan-2026");
    expect(mockRevalidatePath).toHaveBeenCalledWith("/e/openclaw-wuhan-2026");
  });
});

describe("revalidateEventList", () => {
  beforeEach(() => {
    mockRevalidatePath.mockClear();
  });

  it("revalidates both homepage and past events page", async () => {
    await revalidateEventList();
    expect(mockRevalidatePath).toHaveBeenCalledWith("/");
    expect(mockRevalidatePath).toHaveBeenCalledWith("/past");
    expect(mockRevalidatePath).toHaveBeenCalledTimes(2);
  });
});
