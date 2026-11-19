import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("Supabase browser configuration safety", () => {
  it("keeps accounts unavailable when project settings are missing", async () => {
    vi.stubEnv("VITE_SUPABASE_AUTH_ENABLED", "true");
    vi.stubEnv("VITE_SUPABASE_URL", "");
    vi.stubEnv("VITE_SUPABASE_PUBLISHABLE_KEY", "");
    const module = await import("./supabaseClient");
    await expect(module.createSupabaseClient()).resolves.toBeNull();
    expect(module.supabaseConfigurationAvailable).toBe(false);
  });

  it("rejects a JWT whose role identifies it as a service-role key", async () => {
    vi.stubEnv("VITE_SUPABASE_AUTH_ENABLED", "true");
    vi.stubEnv("VITE_SUPABASE_URL", "https://development-project.supabase.co");
    const payload = btoa(JSON.stringify({ role: "service_role" })).replace(/=/g, "");
    vi.stubEnv("VITE_SUPABASE_PUBLISHABLE_KEY", "eyJhbGciOiJub25lIn0." + payload + ".signature");
    const module = await import("./supabaseClient");
    expect(module.supabaseConfiguration).toBeNull();
    await expect(module.createSupabaseClient()).resolves.toBeNull();
  });

  it("accepts an opaque publishable key and an HTTPS project URL without connecting during import", async () => {
    vi.stubEnv("VITE_SUPABASE_AUTH_ENABLED", "true");
    vi.stubEnv("VITE_SUPABASE_URL", "https://development-project.supabase.co");
    vi.stubEnv("VITE_SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test-placeholder");
    const module = await import("./supabaseClient");
    expect(module.supabaseConfigurationAvailable).toBe(true);
    expect(module.supabaseConfiguration?.url).toBe("https://development-project.supabase.co");
  });

  it("ignores even configured project details when the release gate is disabled", async () => {
    vi.stubEnv("VITE_SUPABASE_AUTH_ENABLED", "false");
    vi.stubEnv("VITE_SUPABASE_URL", "https://development-project.supabase.co");
    vi.stubEnv("VITE_SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test-placeholder");
    const module = await import("./supabaseClient");
    expect(module.accountAuthEnabled).toBe(false);
    expect(module.supabaseConfigurationAvailable).toBe(false);
    expect(module.supabaseConfiguration).toBeNull();
    await expect(module.createSupabaseClient()).resolves.toBeNull();
  });

  it("allows callbacks only to the official production, staging, and local origins", async () => {
    vi.stubEnv("VITE_SUPABASE_AUTH_ENABLED", "true");
    const { isAllowedAuthOrigin, safeAuthCallbackUrl } = await import("./supabaseClient");
    expect(safeAuthCallbackUrl("https://trade.jujosmi.com")).toBe("https://trade.jujosmi.com/");
    expect(safeAuthCallbackUrl("https://jujosmi-trade-v2.onrender.com")).toBe("https://jujosmi-trade-v2.onrender.com/");
    expect(safeAuthCallbackUrl("http://localhost:5173")).toBe("http://localhost:5173/");
    expect(safeAuthCallbackUrl("http://127.0.0.1:5177")).toBe("http://127.0.0.1:5177/");
    expect(safeAuthCallbackUrl("http://localhost")).toBe("http://localhost/");
    for (const origin of [
      "https://trade.jujosmi.com.attacker.test",
      "http://trade.jujosmi.com",
      "https://unapproved.example",
      "https://trade.jujosmi.com/path",
      "https://user@trade.jujosmi.com",
      "http://localhost:80",
    ]) expect(isAllowedAuthOrigin(origin)).toBe(false);
  });
});
