"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { downloadProjectFile, myOrders, myProjects } from "../../lib/api";
import { getToken, subscribe } from "../../lib/auth";

export default function DashboardPage() {
  const [ready, setReady] = useState(false);
  const [token, setToken] = useState(null);
  const [listings, setListings] = useState(null);
  const [orders, setOrders] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    const sync = () => {
      const current = getToken();
      setToken(current);
      setReady(true);
      if (!current) {
        setListings(null);
        setOrders(null);
        return;
      }
      myProjects(current).then(setListings).catch((err) => setError(err.message));
      myOrders(current).then(setOrders).catch((err) => setError(err.message));
    };
    sync();
    return subscribe(sync);
  }, []);

  async function download(order) {
    setBusy(`order-${order.id}`);
    setError("");
    try {
      await downloadProjectFile(token, order.project_id, `${order.project_title || order.project_id}.zip`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  if (ready && !token) {
    return (
      <div className="empty">
        <p className="empty-title">Sign in to see your dashboard</p>
        <p className="row-meta">Your listings, their quality scores and everything you bought live here.</p>
        <Link className="btn btn-primary" href="/login">
          Sign in
        </Link>
      </div>
    );
  }

  return (
    <>
      <div className="page-head">
        <h1 className="page-title">Dashboard</h1>
        <p className="meta-line">Your listings and everything you bought.</p>
      </div>

      {error ? <p className="error-note">{error}</p> : null}

      <h2 className="section-title">My listings</h2>
      {listings === null ? (
        <p className="loading-note">Loading your listings…</p>
      ) : listings.length === 0 ? (
        <div className="empty">
          <p className="empty-title">Nothing listed yet</p>
          <p className="row-meta">Paste a README and the local model drafts the listing for you.</p>
          <Link className="btn btn-primary" href="/sell/new">
            List a project
          </Link>
        </div>
      ) : (
        <div className="rows">
          {listings.map((project) => (
            <div className="row" key={project.id}>
              <div className="row-main">
                <h3 className="row-title">
                  <Link href={`/projects/${project.id}`}>{project.title || "Untitled draft"}</Link>
                </h3>
                <p className="row-meta">
                  {project.status === "published" ? "Published" : "Draft"} · ₹{project.price_inr} ·
                  quality check {project.ai_score === null || project.ai_score === undefined ? "not run" : `${project.ai_score}/100`}{" "}
                  · ZIP {project.has_file ? "attached" : "missing"}
                </p>
              </div>
              <Link className="btn btn-quiet" href="/sell/new">
                Edit
              </Link>
            </div>
          ))}
        </div>
      )}

      <h2 className="section-title">My purchases</h2>
      {orders === null ? (
        <p className="loading-note">Loading your purchases…</p>
      ) : orders.length === 0 ? (
        <div className="empty">
          <p className="empty-title">Nothing bought yet</p>
          <p className="row-meta">Browse the board and ask the model about any project first.</p>
          <Link className="btn btn-primary" href="/">
            Go to the board
          </Link>
        </div>
      ) : (
        <div className="rows">
          {orders.map((order) => (
            <div className="row" key={order.id}>
              <div className="row-main">
                <h3 className="row-title">
                  <Link href={`/projects/${order.project_id}`}>{order.project_title || `Project ${order.project_id}`}</Link>
                </h3>
                <p className="row-meta">
                  ₹{order.amount_inr} · {order.provider} ·{" "}
                  <span className={order.status === "paid" ? "status-paid" : "status-pending"}>
                    {order.status}
                  </span>
                </p>
              </div>
              {order.status === "paid" ? (
                <button
                  className="btn btn-primary"
                  type="button"
                  onClick={() => download(order)}
                  disabled={busy === `order-${order.id}`}
                >
                  {busy === `order-${order.id}` ? "Getting the ZIP…" : "Download ZIP"}
                </button>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
