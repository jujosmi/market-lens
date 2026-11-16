import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Session, SupabaseClient, User } from "@supabase/supabase-js";
import type { Database } from "./database.types";
import { createSupabaseClient, supabaseConfigurationAvailable } from "./supabaseClient";

export type AuthContextValue = {
  client: SupabaseClient<Database> | null;
  configured: boolean;
  loading: boolean;
  user: User | null;
  signInWithEmail: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [client, setClient] = useState<SupabaseClient<Database> | null>(null);
  const [session, setSession] = useState<Session | null>(null);
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
    let active = true;
    const { data: { subscription } } = client.auth.onAuthStateChange((_event, nextSession) => {
      if (!active) return;
      setSession(nextSession);
      setLoading(false);
    });
    void client.auth.getSession().then(({ data, error }) => {
      if (!active) return;
      setSession(error ? null : data.session);
      setLoading(false);
    }).catch(() => {
      if (active) { setSession(null); setLoading(false); }
    });
    return () => { active = false; subscription.unsubscribe(); };
  }, [client]);

  const value = useMemo<AuthContextValue>(() => ({
    client,
    configured: supabaseConfigurationAvailable && client !== null,
    loading,
    user: session?.user ?? null,
    async signInWithEmail(email) {
      if (!client) throw new Error("Account sign-in is unavailable until Supabase is configured.");
      const address = email.trim();
      if (!address || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address)) throw new Error("Enter a valid email address.");
      const callbackUrl = window.location.origin;
      const { error } = await client.auth.signInWithOtp({
        email: address,
        options: { emailRedirectTo: callbackUrl, shouldCreateUser: true },
      });
      if (error) throw new Error("Could not send the sign-in link. Check Supabase Auth and email delivery settings, then try again.");
    },
    async signOut() {
      if (!client) return;
      const { error } = await client.auth.signOut({ scope: "local" });
      if (error) throw new Error("Could not sign out. Try again.");
      setSession(null);
    },
  }), [client, loading, session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider.");
  return value;
}
