import { tradingViewTickerSymbols } from "./data/tradingViewSymbols";

export const PREFERENCES_KEY = "jujosmi_trade_ui_preferences_v1";

export type AppPreferences = {
  reduceAnimations: boolean;
  defaultSymbol: string;
  sidebarCollapsed: boolean;
};

export const DEFAULT_PREFERENCES: AppPreferences = {
  reduceAnimations: false,
  defaultSymbol: "NVDA",
  sidebarCollapsed: false,
};

export function readPreferences(systemReducedMotion = false): AppPreferences {
  const defaults = { ...DEFAULT_PREFERENCES, reduceAnimations: systemReducedMotion };
  try {
    const stored = window.localStorage.getItem(PREFERENCES_KEY);
    if (!stored) return defaults;
    const value: unknown = JSON.parse(stored);
    if (!value || typeof value !== "object" || Array.isArray(value)) return defaults;
    const candidate = value as Partial<AppPreferences>;
    return {
      reduceAnimations: systemReducedMotion || candidate.reduceAnimations === true,
      defaultSymbol: typeof candidate.defaultSymbol === "string" && tradingViewTickerSymbols.includes(candidate.defaultSymbol)
        ? candidate.defaultSymbol
        : defaults.defaultSymbol,
      sidebarCollapsed: typeof candidate.sidebarCollapsed === "boolean" ? candidate.sidebarCollapsed : defaults.sidebarCollapsed,
    };
  } catch {
    return defaults;
  }
}

export function writePreferences(preferences: AppPreferences) {
  try {
    window.localStorage.setItem(PREFERENCES_KEY, JSON.stringify({
      reduceAnimations: preferences.reduceAnimations === true,
      defaultSymbol: tradingViewTickerSymbols.includes(preferences.defaultSymbol) ? preferences.defaultSymbol : DEFAULT_PREFERENCES.defaultSymbol,
      sidebarCollapsed: preferences.sidebarCollapsed === true,
    } satisfies AppPreferences));
  } catch {
    // The current browser session still uses in-memory preferences if storage is blocked.
  }
}
