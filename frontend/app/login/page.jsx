"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { login, me, register } from "../../lib/api";
import { saveSession } from "../../lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState("signin");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const signingIn = mode === "signin";

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const session = signingIn
        ? await login({ email, password })
        : await register({ email, name, password });
      const user = await me(session.access_token);
      saveSession(session.access_token, user);
      router.push("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="prose">
      <div className="page-head">
        <h1 className="page-title">{signingIn ? "Sign in" : "Create an account"}</h1>
        <p className="meta-line">
          One account buys projects and lists them. Passwords are hashed with bcrypt, sessions are
          JWTs.
        </p>
      </div>

      {error ? <p className="error-note">{error}</p> : null}

      <form onSubmit={submit}>
        {!signingIn ? (
          <label className="field">
            <span className="field-label">Your name</span>
            <input
              className="input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
            />
          </label>
        ) : null}

        <label className="field">
          <span className="field-label">Email</span>
          <input
            className="input"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>

        <label className="field">
          <span className="field-label">Password</span>
          <input
            className="input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={signingIn ? undefined : 8}
            required
          />
          {!signingIn ? <p className="hint">At least 8 characters.</p> : null}
        </label>

        <div className="btn-row">
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "Working…" : signingIn ? "Sign in" : "Create account"}
          </button>
          <button
            className="btn btn-quiet"
            type="button"
            onClick={() => {
              setMode(signingIn ? "register" : "signin");
              setError("");
            }}
          >
            {signingIn ? "I need an account" : "I already have one"}
          </button>
        </div>
      </form>

      <p className="hint">
        Demo sellers from <code>seed.py</code>: ananya@example.com or rahul@example.com, password
        launchpad123. <Link href="/">Back to the board</Link>
      </p>
    </div>
  );
}
