import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
const authMocks = vi.hoisted(() => ({
  createSupabaseClient: vi.fn(),
}));

vi.mock("./supabaseClient", () => ({
  accountAuthEnabled: true,
  createSupabaseClient: authMocks.createSupabaseClient,
  supabaseConfigurationAvailable: true,
  publicSignupEnabled: false,
  safeAuthCallbackUrl: (origin: string) => origin === "http://localhost" || origin === "http://localhost:5173" ? `${origin}/` : null,
}));

import { AuthProvider, useAuth } from "./AuthContext";

const testUser = { id: "user-a", email: "a@example.test" };
const testSession = { user: testUser, access_token: "test-access-token", refresh_token: "test-refresh-token", expires_at: 9999999999 };

function makeClient() {
  return {
    auth: {
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
      getSession: vi.fn(async (): Promise<{ data: { session: typeof testSession | null }; error: null }> => ({ data: { session: null }, error: null })),
      verifyOtp: vi.fn(async () => ({ data: { session: testSession, user: testUser }, error: null })),
      signInWithOtp: vi.fn(async () => ({ error: null })),
      signOut: vi.fn(async () => ({ error: null })),
    },
  };
}

function Probe() {
  const auth = useAuth();
  return <div><span>{auth.user?.email ?? "guest"}</span><span>{auth.loading ? "loading" : "ready"}</span>
    <button onClick={() => void auth.signInWithEmail("a@example.test")}>request link</button>
    <button onClick={() => void auth.signOut()}>sign out</button>
    <span>{auth.feedback?.message ?? "no notice"}</span></div>;
}

afterEach(() => {
  vi.clearAllMocks();
  window.history.replaceState({}, "", "/");
});

describe("Supabase auth provider lifecycle", () => {
  it("verifies PKCE-compatible email token hashes and restores only a real session", async () => {
    const client = makeClient();
    authMocks.createSupabaseClient.mockResolvedValue(client);
    window.history.replaceState({}, "", "/?token_hash=one-time&type=email");
    render(<AuthProvider><Probe /></AuthProvider>);

    await screen.findByText("a@example.test");
    expect(client.auth.verifyOtp).toHaveBeenCalledWith({ token_hash: "one-time", type: "email" });
    expect(window.location.search).toBe("");
    expect(screen.getByText("Email verified. You are signed in on this browser.")).toBeInTheDocument();
  });

  it("uses only the exact approved application origin and keeps public signup disabled by default", async () => {
    const client = makeClient();
    authMocks.createSupabaseClient.mockResolvedValue(client);
    render(<AuthProvider><Probe /></AuthProvider>);
    await waitFor(() => expect(screen.getByText("ready")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "request link" }));
    await waitFor(() => expect(client.auth.signInWithOtp).toHaveBeenCalledWith({
      email: "a@example.test",
      options: { emailRedirectTo: `${window.location.origin}/`, shouldCreateUser: false },
    }));
  });

  it("clears the local authenticated state after a successful sign-out", async () => {
    const client = makeClient();
    client.auth.getSession.mockResolvedValue({ data: { session: testSession }, error: null });
    authMocks.createSupabaseClient.mockResolvedValue(client);
    render(<AuthProvider><Probe /></AuthProvider>);
    await screen.findByText("a@example.test");
    fireEvent.click(screen.getByRole("button", { name: "sign out" }));
    await screen.findByText("guest");
    expect(client.auth.signOut).toHaveBeenCalledWith({ scope: "local" });
  });
});
