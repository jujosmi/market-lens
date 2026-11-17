import { afterEach, describe, expect, it } from "vitest";
import { DEFAULT_PREFERENCES, PREFERENCES_KEY, readPreferences, writePreferences } from "./preferences";

afterEach(() => window.localStorage.clear());

describe("browser-local preferences", () => {
  it("uses defaults and the operating-system reduced-motion preference when there is no saved value", () => {
    expect(readPreferences(false)).toEqual(DEFAULT_PREFERENCES);
    expect(readPreferences(true)).toEqual({ ...DEFAULT_PREFERENCES, reduceAnimations: true });
  });

  it("validates stored values and never disables operating-system reduced motion", () => {
    window.localStorage.setItem(PREFERENCES_KEY, JSON.stringify({ reduceAnimations: false, defaultSymbol: "NOT_SUPPORTED", sidebarCollapsed: true, email: "private@example.test" }));
    expect(readPreferences(true)).toEqual({ reduceAnimations: true, defaultSymbol: "NVDA", sidebarCollapsed: true });
    expect(readPreferences(false)).toEqual({ reduceAnimations: false, defaultSymbol: "NVDA", sidebarCollapsed: true });
  });

  it("recovers from malformed storage and saves only supported non-sensitive settings", () => {
    window.localStorage.setItem(PREFERENCES_KEY, "{broken json");
    expect(readPreferences()).toEqual(DEFAULT_PREFERENCES);
    writePreferences({ reduceAnimations: true, defaultSymbol: "AAPL", sidebarCollapsed: true });
    expect(JSON.parse(window.localStorage.getItem(PREFERENCES_KEY) ?? "{}")).toEqual({ reduceAnimations: true, defaultSymbol: "AAPL", sidebarCollapsed: true });
  });
});
