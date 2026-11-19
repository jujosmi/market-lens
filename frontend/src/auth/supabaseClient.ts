import type { SupabaseClient } from "@supabase/supabase-js";
import type { Database } from "./database.types";
import { isAccountAuthEnabled } from "../releaseFeatures";

export type SupabaseConfiguration = { url: string; publishableKey: string };

const exactHostedAuthOrigins = new Set([
  "https://trade.jujosmi.com",
  "https://jujosmi-trade-v2.onrender.com",
]);

/** Only the official app, staging app and local Vite development origins may receive an auth callback. */
export function isAllowedAuthOrigin(origin: string): boolean {
  try {
    const parsed = new URL(origin);
    if (parsed.origin !== origin || parsed.username || parsed.password || parsed.pathname !== "/" || parsed.search || parsed.hash) return false;
    if (exactHostedAuthOrigins.has(parsed.origin)) return true;
    const localHost = parsed.hostname === "localhost" || parsed.hostname === "127.0.0.1";
    const localPort = Number(parsed.port);
    return localHost && parsed.protocol === "http:" && (!parsed.port || (localPort >= 1024 && localPort <= 65535));
  } catch {
    return false;
  }
}

export function safeAuthCallbackUrl(origin: string): string | null {
  return isAllowedAuthOrigin(origin) ? `${origin}/` : null;
}

function readConfiguration(): SupabaseConfiguration | null {
  const env = import.meta.env as ImportMetaEnv & {
    VITE_SUPABASE_URL?: string;
    VITE_SUPABASE_PUBLISHABLE_KEY?: string;
  };
  const url = env.VITE_SUPABASE_URL?.trim() ?? "";
  const publishableKey = env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim() ?? "";
  if (!url || !publishableKey) return null;

  try {
    const parsed = new URL(url);
    const secure = parsed.protocol === "https:";
    const localHttp = parsed.protocol === "http:" && (parsed.hostname === "localhost" || parsed.hostname === "127.0.0.1");
    if (!secure && !localHttp) return null;
  } catch {
    return null;
  }

  if (/^sb_secret_/i.test(publishableKey) || /service[_ -]?role/i.test(publishableKey)) return null;
  if (publishableKey.startsWith("eyJ")) {
    try {
      const payload = publishableKey.split(".")[1];
      if (payload && JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/"))).role === "service_role") return null;
    } catch {
      // Supabase publishable keys can be opaque; only a positively identified service key is rejected here.
    }
  }
  return { url, publishableKey };
}

export const accountAuthEnabled = isAccountAuthEnabled();
export const supabaseConfiguration = accountAuthEnabled ? readConfiguration() : null;
export const supabaseConfigurationAvailable = supabaseConfiguration !== null;
export const publicSignupEnabled = accountAuthEnabled
  && (import.meta.env as ImportMetaEnv & { VITE_SUPABASE_PUBLIC_SIGNUP?: string }).VITE_SUPABASE_PUBLIC_SIGNUP === "true";

export async function createSupabaseClient(): Promise<SupabaseClient<Database> | null> {
  if (!supabaseConfiguration) return null;
  const { createClient } = await import("@supabase/supabase-js");
  return createClient<Database>(supabaseConfiguration.url, supabaseConfiguration.publishableKey, {
    auth: {
      flowType: "pkce",
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
    },
  });
}
