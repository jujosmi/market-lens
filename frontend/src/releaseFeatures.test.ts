import { describe, expect, it } from "vitest";
import { isAccountAuthEnabled, isTradingViewWidgetEnabled, resolveApiBaseUrl } from "./releaseFeatures";

describe("release feature gates", () => {
  it("keeps optional account access off unless explicitly enabled", () => {
    expect(isAccountAuthEnabled({ VITE_SUPABASE_AUTH_ENABLED: undefined })).toBe(false);
    expect(isAccountAuthEnabled({ VITE_SUPABASE_AUTH_ENABLED: "false" })).toBe(false);
    expect(isAccountAuthEnabled({ VITE_SUPABASE_AUTH_ENABLED: "true" })).toBe(true);
  });

  it("keeps the TradingView embed in local development but requires production opt-in", () => {
    expect(isTradingViewWidgetEnabled({ DEV: true })).toBe(true);
    expect(isTradingViewWidgetEnabled({ DEV: true, VITE_TRADINGVIEW_WIDGET_ENABLED: "false" })).toBe(false);
    expect(isTradingViewWidgetEnabled({ DEV: false })).toBe(false);
    expect(isTradingViewWidgetEnabled({ DEV: false, VITE_TRADINGVIEW_WIDGET_ENABLED: "true" })).toBe(true);
  });

  it("never falls back to localhost for a production API base", () => {
    expect(resolveApiBaseUrl({ DEV: true })).toBe("http://127.0.0.1:8000/api/v1");
    expect(resolveApiBaseUrl({ DEV: false })).toBe("");
    expect(resolveApiBaseUrl({ DEV: false, VITE_TRADE_API_BASE_URL: " https://api.example.test/api/v1/ " })).toBe("https://api.example.test/api/v1");
  });
});
