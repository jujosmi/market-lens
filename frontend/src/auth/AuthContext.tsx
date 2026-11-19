import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Session, SupabaseClient, User } from "@supabase/supabase-js";
import type { Database } from "./database.types";
import { cleanAuthCallbackUrl, authFailureMessage, readAuthCallback } from "./authCallback";
import { accountAuthEnabled, createSupabaseClient, publicSignupEnabled, safeAuthCallbackUrl, supabaseConfigurationAvailable } from "./supabaseClient";

export type AuthFeedback = { kind: "success" | "error"; message: string };

export type AuthContextValue = {
  client: SupabaseClient<Database> | null;
  enabled: boolean;
  configured: boolean;
  loading: boolean;
  user: User | null;
  feedback: AuthFeedback | null;
  dismissFeedback: () => void;
  signInWithEmail: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [client, setClient] = useState<SupabaseClient<Database> | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [feedback, setFeedback] = useState<AuthFeedback | null>(null);
  const [loading, setLoading] = useState(supabaseConfigurationAvailable);

  useEffect(() => {
    if (!supabaseConfigurationAvailable) {
      setLoading(false);
      return;
    }
    let active = true;
    void createSupabaseClient().then((created) => {
      if (active) setClient(created);
    }).catch(() => {
      if (active) { setClient(null); setSession(null); setLoading(false); }
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!client) {
      if (!supabaseConfigurationAvailable) setLoading(false);
      return;
    }
    const activeClient = client;
    let active = true;
    const { data: { subscription } } = activeClient.auth.onAuthStateChange((_event, nextSession) => {
      if (!active) return;
      setSession(nextSession);
      setLoading(false);
    });
    async function restoreOrVerifyCallback() {
      const callback = readAuthCallback(window.location.href);
      if (callback.kind !== "none") window.history.replaceState(window.history.state, "", cleanAuthCallbackUrl(window.location.href));
      if (callback.kind === "error") {
        setFeedback({ kind: "error", message: callback.message });
      } else if (callback.kind === "verify-email") {
        setLoading(true);
        try {
          const { data, error } = await activeClient.auth.verifyOtp({ token_hash: callback.tokenHash, type: "email" });
          if (!active) return;
          if (error || !data.session || !data.user) {
            setSession(null);
            setFeedback({ kind: "error", message: authFailureMessage(error) });
          } else {
            setSession(data.session);
            setFeedback({ kind: "success", message: "Email verified. You are signed in on this browser." });
          }
        } catch (error) {
          if (active) { setSession(null); setFeedback({ kind: "error", message: authFailureMessage(error) }); }
        } finally {
          if (active) setLoading(false);
        }
        return;
      }
      try {
        const { data, error } = await activeClient.auth.getSession();
        if (!active) return;
        setSession(error ? null : data.session);
        if (error) setFeedback({ kind: "error", message: "Your saved sign-in could not be restored. Try signing in again." });
      } catch {
        if (active) { setSession(null); setFeedback({ kind: "error", message: "Your saved sign-in could not be restored. Try signing in again." }); }
      } finally {
        if (active) setLoading(false);
      }
    }
    void restoreOrVerifyCallback();
    return () => { active = false; subscription.unsubscribe(); };
  }, [client]);

  const value = useMemo<AuthContextValue>(() => ({
    client,
    enabled: accountAuthEnabled,
    configured: accountAuthEnabled && supabaseConfigurationAvailable && client !== null && safeAuthCallbackUrl(window.location.origin) !== null,
    loading,
    user: session?.user ?? null,
    feedback,
    dismissFeedback() { setFeedback(null); },
    async signInWithEmail(email) {
      if (!client) throw new Error("Account sign-in is unavailable until Supabase is configured.");
      const address = email.trim();
      if (!address || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address)) throw new Error("Enter a valid email address.");
      const callbackUrl = safeAuthCallbackUrl(window.location.origin);
      if (!callbackUrl) throw new Error("Sign-in is unavailable from this application address.");
      setFeedback(null);
      const { error } = await client.auth.signInWithOtp({
        email: address,
        options: { emailRedirectTo: callbackUrl, shouldCreateUser: publicSignupEnabled },
      });
      if (error) throw new Error(authFailureMessage(error));
    },
    async signOut() {
      if (!client) return;
      const { error } = await client.auth.signOut({ scope: "local" });
      if (error) throw new Error("Could not sign out. Try again.");
      setSession(null);
      setFeedback({ kind: "success", message: "Signed out on this browser." });
    },
  }), [client, feedback, loading, session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider.");
  return value;
}
