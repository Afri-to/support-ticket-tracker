import { useState, type FormEvent } from "react";
import { api } from "../api";
import type { User } from "../types";

type Mode = "signin" | "register";

/** Sign in, create an account, or look around the read-only demo. */
export function SignIn({ onSignedIn }: { onSignedIn: (u: User) => void }) {
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<User>) {
    setBusy(true);
    setError(null);
    try {
      onSignedIn(await action());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    run(() => (mode === "signin" ? api.login(email, password) : api.register(email, password)));
  }

  const switchTo = (m: Mode) => {
    setMode(m);
    setError(null);
  };

  return (
    <div className="auth">
      <div className="auth-intro">
        <h1>Support Ticket Tracker</h1>
        <p>
          Import support tickets from a CSV export, clean out duplicates and bad rows, and see weekly KPIs: volume,
          time to resolve, root causes and agent workload.
        </p>
        <button type="button" className="primary" onClick={() => run(api.demo)} disabled={busy}>
          Explore the demo
        </button>
        <p className="muted small">Read-only, with 4,789 fake tickets already imported. No account needed.</p>
      </div>

      <form className="card auth-card" onSubmit={submit} noValidate>
        <h2>{mode === "signin" ? "Sign in" : "Create an account"}</h2>
        <label className="field">
          Email
          <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label className="field">
          Password
          <input
            type="password"
            autoComplete={mode === "signin" ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </label>
        {mode === "register" && <p className="muted small">At least 8 characters.</p>}
        {error && <p className="error-text" role="alert">{error}</p>}
        <button type="submit" className="primary" disabled={busy}>
          {mode === "signin" ? "Sign in" : "Create account"}
        </button>
        <p className="small">
          {mode === "signin" ? (
            <>New here? <button type="button" className="link-button" onClick={() => switchTo("register")}>Create an account</button></>
          ) : (
            <>Have an account? <button type="button" className="link-button" onClick={() => switchTo("signin")}>Sign in</button></>
          )}
        </p>
      </form>
    </div>
  );
}
