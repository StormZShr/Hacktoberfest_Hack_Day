"use client";

import { useState } from "react";
import { askProject } from "../lib/api";

// A3: answers come only from this project's listing and README. The note under
// the answer says which of the two happened, so a buyer never mistakes a
// grounded answer for a guarantee.
export default function AskBox({ projectId }) {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(await askProject(projectId, question.trim()));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ask">
      <h3 className="panel-title">Ask about this project</h3>
      <p className="row-meta">
        The answer comes only from this listing and its README, using the model running on this
        machine.
      </p>
      <form onSubmit={submit}>
        <div className="ask-row">
          <label className="field search-input">
            <span className="field-label">Your question</span>
            <input
              className="input"
              value={question}
              maxLength={500}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Does it include login? How do I run it?"
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={busy || !question.trim()}>
            {busy ? "Asking…" : "Ask"}
          </button>
        </div>
      </form>

      {busy ? <p className="loading-note">Asking the local model…</p> : null}
      {error ? <p className="error-note">{error}</p> : null}

      {result ? (
        <div className="ask-answer">
          <p className="grounded-note" data-grounded={result.in_listing ? "true" : "false"}>
            {result.in_listing ? "In the listing" : "Not in the listing"}
          </p>
          <p>{result.answer}</p>
        </div>
      ) : null}
    </div>
  );
}
