import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("Supabase browser configuration safety", () => {
  it("keeps accounts unavailable when project settings are missing", async () => {
    vi.stubEnv("VITE_SUPABASE_URL", "");
    vi.stubEnv("VITE_SUPABASE_PUBLISHABLE_KEY", "");
    const module = await import("./supabaseClient");
    await expect(module.createSupabaseClient()).resolves.toBeNull();
    expect(module.supabaseConfigurationAvailable).toBe(false);
  });

  it("rejects a JWT whose role identifies it as a service-role key", async () => {
    vi.stubEnv("VITE_SUPABASE_URL", "https://development-project.supabase.co");
    const payload = btoa(JSON.stringify({ role: "service_role" })).replace(/=/g, "");
    vi.stubEnv("VITE_SUPABASE_PUBLISHABLE_KEY", "eyJhbGciOiJub25lIn0." + payload + ".signature");
    const module = await import("./supabaseClient");
    expect(module.supabaseConfiguration).toBeNull();
    await expect(module.createSupabaseClient()).resolves.toBeNull();
  });

  it("accepts an opaque publishable key and an HTTPS project URL without connecting during import", async () => {
    vi.stubEnv("VITE_SUPABASE_URL", "https://development-project.supabase.co");
    vi.stubEnv("VITE_SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test-placeholder");
    const module = await import("./supabaseClient");
    expect(module.supabaseConfigurationAvailable).toBe(true);
    expect(module.supabaseConfiguration?.url).toBe("https://development-project.supabase.co");
  });
});
