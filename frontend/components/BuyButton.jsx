"use client";

import Link from "next/link";
import { useState } from "react";
import { confirmOrder, createOrder, downloadProjectFile } from "../lib/api";

function zipName(title, id) {
  const safe = (title || `project-${id}`).replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "");
  return `${safe || `project-${id}`}.zip`;
}

// Mock provider: the order is created and confirmed in one go, and the button
// says so. No real money moves anywhere in this app.
export default function BuyButton({ project, token, user, owned, onOwned }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const isSeller = Boolean(user) && user.id === project.seller_id;
  const canDownload = isSeller || owned;

  async function buy() {
    setBusy(true);
    setError("");
    setNote("");
    try {
      const order = await createOrder(token, project.id);
      await confirmOrder(token, order.id);
      setNote("Paid in test mode. The ZIP is ready to download.");
      if (onOwned) onOwned();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function download() {
    setBusy(true);
    setError("");
    try {
      await downloadProjectFile(token, project.id, zipName(project.title, project.id));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <div className="panel">
        <h3 className="panel-title">Get this project</h3>
        <p className="price-tag">₹{project.price_inr}</p>
        <p className="row-meta">Sign in to buy and download the ZIP.</p>
        <Link className="btn btn-primary" href="/login">
          Sign in to buy
        </Link>
        <p className="hint">Checkout runs in test mode. No real money moves.</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <h3 className="panel-title">{isSeller ? "Your listing" : "Get this project"}</h3>
      <p className="price-tag">₹{project.price_inr}</p>

      {isSeller ? (
        <p className="row-meta">
          You are the seller. Buyers see the quality stamp and the demo talking points, never your
          README.
        </p>
      ) : null}

      {error ? <p className="error-note">{error}</p> : null}
      {note ? <p className="ok-note">{note}</p> : null}

      <div className="btn-row">
        {canDownload ? (
          <button className="btn btn-primary" type="button" onClick={download} disabled={busy}>
            {busy ? "Getting the ZIP…" : "Download ZIP"}
          </button>
        ) : (
          <button className="btn btn-tag" type="button" onClick={buy} disabled={busy}>
            {busy ? "Working…" : `Buy for ₹${project.price_inr}`}
          </button>
        )}
      </div>

      {!canDownload ? <p className="hint">Test checkout with the mock provider. No real money moves.</p> : null}
    </div>
  );
}
