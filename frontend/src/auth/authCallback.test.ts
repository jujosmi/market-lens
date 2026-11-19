import { describe, expect, it } from "vitest";
import { authFailureMessage, cleanAuthCallbackUrl, readAuthCallback } from "./authCallback";

describe("Supabase email callback parsing", () => {
  it("accepts only email token hashes and does not invent a callback route", () => {
    expect(readAuthCallback("https://trade.jujosmi.com/?token_hash=one-time-hash&type=email"))
      .toEqual({ kind: "verify-email", tokenHash: "one-time-hash" });
    expect(readAuthCallback("https://trade.jujosmi.com/?token_hash=one-time-hash&type=recovery").kind).toBe("error");
    expect(readAuthCallback("https://trade.jujosmi.com/research?code=pkce-code").kind).toBe("none");
  });

  it("maps expired and rate limited callbacks to safe, actionable messages", () => {
    expect(readAuthCallback("https://trade.jujosmi.com/?error_code=otp_expired&error_description=private-value"))
      .toEqual({ kind: "error", message: "This sign-in link expired or was already used. Request a new link and open it in the same browser." });
    expect(authFailureMessage({ status: 429, message: "over_email_send_rate_limit" })).toContain("Wait a little");
    expect(readAuthCallback("https://trade.jujosmi.com/#error=access_denied&error_description=private-value").kind).toBe("error");
    expect(JSON.stringify(readAuthCallback("https://trade.jujosmi.com/#error=access_denied&error_description=private-value"))).not.toContain("private-value");
  });

  it("removes one-time callback data while preserving the app path and unrelated query values", () => {
    expect(cleanAuthCallbackUrl("https://trade.jujosmi.com/discovery?tab=filings&token_hash=secret&type=email"))
      .toBe("/discovery?tab=filings");
  });
});
