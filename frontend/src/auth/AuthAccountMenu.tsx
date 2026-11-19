import { useEffect, useState, type FormEvent } from "react";
import { ChevronDown, LogIn, LogOut, ShieldCheck, UserRound } from "lucide-react";
import { useAuth } from "./AuthContext";

export function AuthAccountMenu() {
  const { enabled, configured, loading, user, feedback, dismissFeedback, signInWithEmail, signOut } = useAuth();
  const [open, setOpen] = useState(Boolean(feedback));
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => { if (feedback) setOpen(true); }, [feedback]);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setNotice("");
    try {
      await signInWithEmail(email);
      setNotice("If the address can sign in, a secure link was requested. Open it in this same browser to finish sign-in.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start sign-in. Try again.");
    } finally { setBusy(false); }
  }

  async function signOutNow() {
    setBusy(true); setError(""); setNotice("");
    try { await signOut(); setNotice("Signed out on this browser."); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not sign out. Try again."); }
    finally { setBusy(false); }
  }

  return <div className="account-menu-wrap">
    <button className="profile-button account-trigger" aria-label={user ? "Account: " + (user.email ?? "signed in") : "Account sign-in"} aria-expanded={open} aria-controls="account-panel" onClick={() => setOpen((value) => !value)}>
      <span className="avatar avatar-small">{user?.email?.slice(0, 1).toUpperCase() ?? <UserRound size={14} />}</span>
      <span className="account-trigger-label">{loading ? "Restoring…" : user ? "Account" : configured ? "Sign in" : "Guest"}</span><ChevronDown size={13} />
    </button>
    {open && <section className="account-panel" id="account-panel" aria-label="Account access">
      <div className="account-panel-heading"><div><span className="section-kicker">JUJOSMI TRADE ACCOUNT</span><h2>{loading ? "Restoring session" : user ? "Signed in" : configured ? "Sign in to sync" : "Guest mode"}</h2></div><span className={"account-status-dot " + (user ? "account-status-active" : "")} aria-label={user ? "Signed in" : "Guest mode"} /></div>
      {loading ? <p role="status">Checking this browser for a saved sign-in…</p> : !enabled ? <>
        <p className="account-panel-copy">Account sign-in is disabled in this release. Guest Company Research and the temporary browser-session watchlist remain available.</p>
        <div className="account-config-note"><ShieldCheck size={14} />No account service is contacted and no session is created.</div>
      </> : user ? <>
        <p className="account-email">{user.email ?? "Signed-in user"}</p><p className="account-panel-copy">Your watchlist is private to this account and governed by database row-level security.</p>
        <button className="account-action" onClick={() => void signOutNow()} disabled={busy}><LogOut size={15} />{busy ? "Signing out…" : "Sign out on this browser"}</button>
      </> : configured ? <>
        <p className="account-panel-copy">Use an email sign-in link for an existing account. Open it in this same browser; public account creation is disabled until the owner completes security testing.</p>
        <form className="account-form" onSubmit={(event) => void submit(event)}>
          <label htmlFor="account-email">Email address</label><input id="account-email" type="email" autoComplete="email" required maxLength={254} value={email} onChange={(event) => setEmail(event.target.value)} />
          <button className="account-action" type="submit" disabled={busy}><LogIn size={15} />{busy ? "Sending link…" : "Email me a sign-in link"}</button>
        </form>
      </> : <>
        <p className="account-panel-copy">Account sync is unavailable because this local build has no Supabase URL and publishable key. Guest research and the temporary watchlist remain available.</p>
        <div className="account-config-note"><ShieldCheck size={14} />No account session is simulated or created.</div>
      </>}
      {notice && <p className="account-message" role="status">{notice}</p>}
      {error && <p className="account-message account-error" role="alert">{error}</p>}
      {feedback && <p className={"account-message " + (feedback.kind === "error" ? "account-error" : "")} role={feedback.kind === "error" ? "alert" : "status"}>{feedback.message}<button className="account-dismiss" onClick={dismissFeedback}>Dismiss</button></p>}
      <button className="account-dismiss" onClick={() => setOpen(false)}>Close</button>
    </section>}
  </div>;
}
