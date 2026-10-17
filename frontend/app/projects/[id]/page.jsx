"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import AskBox from "../../../components/AskBox";
import BuyButton from "../../../components/BuyButton";
import { getProject, myOrders } from "../../../lib/api";
import { getToken, getUser, subscribe } from "../../../lib/auth";

export default function ProjectPage() {
  const params = useParams();
  const id = params.id;

  const [project, setProject] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [owned, setOwned] = useState(false);

  useEffect(() => {
    const sync = () => {
      setToken(getToken());
      setUser(getUser());
    };
    sync();
    return subscribe(sync);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setProject(await getProject(id, getToken()));
    } catch (err) {
      setError(err.message);
      setProject(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!token) {
      setOwned(false);
      return;
    }
    let active = true;
    myOrders(token)
      .then((orders) => {
        if (!active) return;
        setOwned(
          orders.some((order) => order.project_id === Number(id) && order.status === "paid")
        );
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [id, token]);

  if (loading) {
    return <p className="loading-note">Loading the listing…</p>;
  }

  if (!project) {
    return (
      <>
        <p className="error-note">{error || "That project is not on the board."}</p>
        <Link className="btn" href="/">
          Back to the board
        </Link>
      </>
    );
  }

  const isSeller = Boolean(user) && user.id === project.seller_id;

  return (
    <>
      <div className="page-head">
        <h1 className="page-title">{project.title}</h1>
        <p className="meta-line">{project.tagline}</p>
        <p className="meta-line">{project.category || "Uncategorised"}, difficulty: {project.difficulty || "not set"}</p>
      </div>

      <div className="detail-grid">
        <div>
          <div className="prose">
            {project.description
              ? project.description.split("\n").map((paragraph, index) =>
                  paragraph.trim() ? <p key={index}>{paragraph}</p> : null
                )
              : <p className="row-meta">The seller has not written a description yet.</p>}
          </div>

          {project.what_you_get && project.what_you_get.length > 0 ? (
            <div className="panel">
              <h2 className="panel-title">What you get</h2>
              <ul className="bullets">
                {project.what_you_get.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              {project.has_file ? (
                <p className="ok-note">ZIP ready: {project.title}, gated until you buy.</p>
              ) : (
                <p className="hint">The seller has not uploaded the ZIP yet.</p>
              )}
            </div>
          ) : null}

          {project.demo_points && project.demo_points.length > 0 ? (
            <div className="panel">
              <h2 className="panel-title">How the seller demos it</h2>
              <ol className="points">
                {project.demo_points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ol>
            </div>
          ) : null}

          <div className="panel">
            <AskBox projectId={project.id} />
          </div>
        </div>

        <div>
          <BuyButton
            project={project}
            token={token}
            user={user}
            owned={owned}
            onOwned={() => setOwned(true)}
          />

          {project.ai_review ? (
            <div className="panel">
              <h2 className="panel-title">Quality check</h2>
              <p className="review-score">
                <span className="stamp">
                  <span className="stamp-label">Quality check</span>
                  <span className="stamp-score">{project.ai_score}/100</span>
                  <span className="stamp-note">ran on this machine</span>
                </span>
              </p>
              <p className="review-summary">{project.ai_review.summary}</p>
              <p className="row-meta">
                This score is the local model's opinion of the listing, not a guarantee. Read the
                listing before buying.
              </p>
            </div>
          ) : null}

          {project.demo_url ? (
            <div className="panel">
              <h2 className="panel-title">Demo link</h2>
              <p className="row-meta">
                <a href={project.demo_url} target="_blank" rel="noreferrer">
                  {project.demo_url}
                </a>
              </p>
            </div>
          ) : null}

          {isSeller ? (
            <div className="panel">
              <h2 className="panel-title">This is your listing</h2>
              <p className="row-meta">
                Buyers cannot see your README. Manage the listing, its score and its sales on your
                dashboard.
              </p>
              <Link className="btn" href="/dashboard">
                Open dashboard
              </Link>
            </div>
          ) : null}
        </div>
      </div>
    </>
  );
}
