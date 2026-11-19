type ReleaseEnvironment = {
  DEV?: boolean;
  VITE_SUPABASE_AUTH_ENABLED?: string;
  VITE_TRADINGVIEW_WIDGET_ENABLED?: string;
  VITE_TRADE_API_BASE_URL?: string;
};

const environment = import.meta.env as ImportMetaEnv & ReleaseEnvironment;

export function isAccountAuthEnabled(env: ReleaseEnvironment = environment): boolean {
  return env.VITE_SUPABASE_AUTH_ENABLED === "true";
}

/** Keep the embed in local development; public production builds require explicit opt-in. */
export function isTradingViewWidgetEnabled(env: ReleaseEnvironment = environment): boolean {
  if (env.VITE_TRADINGVIEW_WIDGET_ENABLED === "true") return true;
  if (env.VITE_TRADINGVIEW_WIDGET_ENABLED === "false") return false;
  return env.DEV === true;
}

/** Do not send production visitors to their own loopback machine when hosting is unconfigured. */
export function resolveApiBaseUrl(env: ReleaseEnvironment = environment): string {
  const configured = env.VITE_TRADE_API_BASE_URL?.trim();
  if (configured) return configured.replace(/\/+$/, "");
  return env.DEV === true ? "http://127.0.0.1:8000/api/v1" : "";
}
