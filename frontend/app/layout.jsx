"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import "./globals.css";
import { clearSession, getToken, getUser, subscribe } from "../lib/auth";

export default function RootLayout({ children }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const sync = () => setUser(getUser());
    sync();
    return subscribe(sync);
  }, []);

  const signedIn = Boolean(user) && Boolean(getToken());

  return (
    <html lang="en">
      <body>
        <title>Launchpad</title>
        <div className="shell">
          <header className="masthead">
            <div className="masthead-top">
              <Link className="wordmark" href="/">
                Launchpad
              </Link>
              <nav className="nav">
                <Link className="nav-link" href="/">
                  Board
                </Link>
                <Link className="nav-link" href="/sell/new">
                  Sell a project
                </Link>
                {signedIn ? (
                  <>
                    <Link className="nav-link" href="/dashboard">
                      Dashboard
                    </Link>
                    <span className="nav-user">{user.name}</span>
                    <button className="btn btn-quiet" type="button" onClick={() => clearSession()}>
                      Sign out
                    </button>
                  </>
                ) : (
                  <Link className="nav-link" href="/login">
                    Sign in
                  </Link>
                )}
              </nav>
            </div>
            <p className="masthead-line">
              Student projects you can buy, run and keep. Every listing is checked by an open-weight
              model running on this machine.
            </p>
          </header>
          <main>{children}</main>
          <footer className="footer">
            Launchpad runs gemma4:e2b locally through Ollama. A seller's README and code are analysed
            on this machine and never sent to an outside AI service.
          </footer>
        </div>
      </body>
    </html>
  );
}
