export type AuthCallbackState =
  | { kind: "none" }
  | { kind: "verify-email"; tokenHash: string }
  | { kind: "error"; message: string };

type AuthFailureShape = { code?: unknown; status?: unknown; message?: unknown };

export function authFailureMessage(error: unknown): string {
  const candidate = (error && typeof error === "object" ? error : {}) as AuthFailureShape;
  const code = typeof candidate.code === "string" ? candidate.code.toLowerCase() : "";
  const status = Number(candidate.status);
  const message = typeof candidate.message === "string" ? candidate.message.toLowerCase() : "";
  if (status === 429 || code.includes("rate_limit") || code.includes("over_email_send_rate_limit") || message.includes("rate limit")) {
    return "Too many sign-in requests were made. Wait a little before requesting another email link.";
  }
  if (["otp_expired", "token_expired", "flow_state_expired", "bad_code"].some((value) => code.includes(value)) || message.includes("expired or is invalid")) {
    return "This sign-in link expired or was already used. Request a new link and open it in the same browser.";
  }
  return "Sign-in could not be completed. Request a fresh link or try again.";
}

export function readAuthCallback(href: string): AuthCallbackState {
  let url: URL;
  try { url = new URL(href); } catch { return { kind: "none" }; }
  const queryCode = url.searchParams.get("error_code") ?? url.searchParams.get("error");
  const fragment = new URLSearchParams(url.hash.replace(/^#/, ""));
  const fragmentCode = fragment.get("error_code") ?? fragment.get("error");
  if (queryCode || fragmentCode) {
    const code = (queryCode ?? fragmentCode ?? "").toLowerCase();
    const description = (url.searchParams.get("error_description") ?? fragment.get("error_description") ?? "").toLowerCase();
    return { kind: "error", message: authFailureMessage({ code, message: description }) };
  }
  const tokenHash = url.searchParams.get("token_hash");
  const type = url.searchParams.get("type");
  if (tokenHash || type) {
    if (tokenHash && type === "email") return { kind: "verify-email", tokenHash };
    return { kind: "error", message: "This sign-in link could not be verified. Request a new email link." };
  }
  return { kind: "none" };
}

/** Remove one-time hashes, codes, and errors while preserving the selected application path. */
export function cleanAuthCallbackUrl(href: string): string {
  const url = new URL(href);
  for (const key of ["token_hash", "type", "error", "error_code", "error_description"]) url.searchParams.delete(key);
  url.hash = "";
  return `${url.pathname}${url.search}`;
}
