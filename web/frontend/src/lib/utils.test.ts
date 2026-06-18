import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";
import { cn, deadlineBadgeClass, formatDate } from "./utils";

describe("formatDate", () => {
  it("returns em dash for null or undefined", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate(undefined)).toBe("—");
  });

  it("formats valid ISO date in Dutch locale", () => {
    expect(formatDate("2026-03-15")).toBe("15-3-2026");
  });
});

describe("deadlineBadgeClass", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-18T12:00:00"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns muted class when no date", () => {
    expect(deadlineBadgeClass(null)).toBe("bg-muted text-muted-foreground");
  });

  it("returns red for past or today", () => {
    expect(deadlineBadgeClass("2026-06-17")).toBe("bg-red-100 text-red-800");
    expect(deadlineBadgeClass("2026-06-18")).toBe("bg-red-100 text-red-800");
  });

  it("returns amber within 7 days", () => {
    expect(deadlineBadgeClass("2026-06-24")).toBe("bg-amber-100 text-amber-900");
  });

  it("returns emerald for later deadlines", () => {
    expect(deadlineBadgeClass("2026-07-01")).toBe("bg-emerald-100 text-emerald-900");
  });
});

describe("cn", () => {
  it("merges conflicting Tailwind classes", () => {
    expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4");
  });
});
