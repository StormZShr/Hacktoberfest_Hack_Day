"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import ListingForm from "../../../components/ListingForm";
import ReviewPanel from "../../../components/ReviewPanel";
import {
  autofill,
  createProject,
  publishProject,
  reviewListing,
  updateProject,
  uploadProjectFile,
} from "../../../lib/api";
import { getToken, subscribe } from "../../../lib/auth";

const EMPTY_LISTING = {
  title: "",
  tagline: "",
  description: "",
  tech_stack: [],
  category: "",
  difficulty: "",
  what_you_get: [],
  demo_points: [],
  price_inr: 0,
  demo_url: "",
};

export default function SellNewPage() {
  const [ready, setReady] = useState(false);
  const [token, setToken] = useState(null);
  const [readme, setReadme] = useState("");
  const [listing, setListing] = useState(EMPTY_LISTING);
  const [project, setProject] = useState(null);
  const [review, setReview] = useState(null);
  const [fresh, setFresh] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => {
    const sync = () => {
      setToken(getToken());
      setReady(true);
    };
    sync();
    return subscribe(sync);
  }, []);

  async function fillFromReadme() {
    setBusy("autofill");
    setError("");
    setNote("");
    try {
      const result = await autofill(token, readme);
      const { ...fields } = result;
      setListing({ ...EMPTY_LISTING, ...fields });
      setNote("Filled from your README. Read every field and fix anything the model got wrong.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  function payloadFromForm() {
    return { ...listing, readme_text: readme };
  }

  async function saveDraft() {
    setBusy("save");
    setError("");
    setNote("");
    try {
      const saved = project
        ? await updateProject(token, project.id, payloadFromForm())
        : await createProject(token, payloadFromForm());
      setProject(saved);
      setNote(
        saved.status === "published"
          ? "Listing updated. It is live on the board."
          : "Draft saved. Upload the ZIP, then run the quality check."
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function uploadZip(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    if (!project) {
      setError("Save the draft first, then upload the ZIP.");
      event.target.value = "";
      return;
    }
    setBusy("upload");
    setError("");
    setNote("");
    try {
      await uploadProjectFile(token, project.id, file);
      setProject({ ...project, has_file: true });
      setNote(`${file.name} uploaded.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
      event.target.value = "";
    }
  }

  async function checkQuality() {
    if (!project) {
      setError("Save the draft first, then run the check.");
      return;
    }
    setBusy("review");
    setError("");
    setNote("");
    try {
      const result = await reviewListing(token, {
        project_id: project.id,
        readme_text: readme,
      });
      setReview(result);
      setFresh(true);
      setProject({ ...project, ai_score: result.score, ai_review: result });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function publish() {
    setBusy("publish");
    setError("");
    setNote("");
    try {
      const result = await publishProject(token, project.id);
      setProject({ ...project, status: result.status });
      setNote("Published. It is on the board now.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  if (ready && !token) {
    return (
      <div className="empty">
        <p className="empty-title">Sign in to list a project</p>
        <p className="row-meta">
          Your listing, your README and your ZIP stay tied to your account.
        </p>
        <Link className="btn btn-primary" href="/login">
          Sign in
        </Link>
      </div>
    );
  }

  const listingFilled = Boolean(listing.title);
  const publishedOrChecked = project && project.status === "published";

  return (
    <>
      <div className="page-head">
        <h1 className="page-title">List a project</h1>
        <p className="meta-line">
          Paste your README, let the local model draft the listing, then fix it and publish.
        </p>
      </div>

      <div className="steps">
        <span className="step" data-state={readme ? "done" : "next"}>
          <span className="step-dot" />
          Paste your README
        </span>
        <span className="step" data-state={listingFilled ? "done" : readme ? "next" : ""}>
          <span className="step-dot" />
          Fill the listing
        </span>
        <span className="step" data-state={review ? "done" : project ? "next" : ""}>
          <span className="step-dot" />
          Check quality
        </span>
        <span
          className="step"
          data-state={
            publishedOrChecked ? "done" : review ? "next" : project ? "blocked" : ""
          }
        >
          <span className="step-dot" />
          Publish
        </span>
      </div>

      {error ? <p className="error-note">{error}</p> : null}
      {note ? <p className="ok-note">{note}</p> : null}

      <div className="detail-grid">
        <div>
          <label className="field">
            <span className="field-label">Your README or project notes</span>
            <textarea
              className="textarea"
              value={readme}
              onChange={(event) => setReadme(event.target.value)}
              placeholder={"# Project name\n\nWhat it does, how to run it, what is inside…"}
            />
          </label>
          <p className="readme-note">
            This stays on this machine. It is used for the draft, the quality check and buyer
            questions, and it is never shown to a buyer.
          </p>

          <div className="btn-row">
            <button
              className="btn btn-primary"
              type="button"
              onClick={fillFromReadme}
              disabled={busy === "autofill" || readme.trim().length === 0}
            >
              {busy === "autofill" ? "Reading your README…" : "Fill from my README"}
            </button>
            {busy === "autofill" ? (
              <span className="loading-note">The local model is working. On CPU this takes a few seconds.</span>
            ) : null}
          </div>

          <h2 className="section-title">The listing</h2>
          <ListingForm listing={listing} onChange={setListing} />

          <div className="btn-row">
            <button className="btn btn-primary" type="button" onClick={saveDraft} disabled={busy === "save"}>
              {busy === "save" ? "Saving…" : project ? "Save changes" : "Save draft"}
            </button>
            <button className="btn" type="button" onClick={checkQuality} disabled={busy === "review"}>
              {busy === "review" ? "Checking…" : "Check quality"}
            </button>
            <button className="btn btn-tag" type="button" onClick={publish} disabled={busy === "publish" || !project}>
              {busy === "publish" ? "Publishing…" : "Publish"}
            </button>
          </div>

          <div className="panel">
            <h2 className="panel-title">Project ZIP</h2>
            {project ? (
              <>
                <label className="field">
                  <span className="field-label">Upload the ZIP buyers download</span>
                  <input className="input" type="file" accept=".zip" onChange={uploadZip} />
                </label>
                <p className="hint">
                  {project.has_file
                    ? "A ZIP is attached. Uploading another one replaces it."
                    : "ZIP only, up to 25 MB. Publishing needs a ZIP or a demo link."}
                </p>
              </>
            ) : (
              <p className="row-meta">Save the draft first, then attach the ZIP here.</p>
            )}
          </div>
        </div>

        <div>
          <ReviewPanel review={review} busy={busy === "review"} fresh={fresh} />

          {project ? (
            <div className="panel">
              <h2 className="panel-title">Listing state</h2>
              <p className="row-meta">
                {project.status === "published"
                  ? "Published on the board."
                  : "Draft. Only you can see it."}
              </p>
              <p className="row-meta">ZIP attached: {project.has_file ? "yes" : "no"}</p>
              {project.status === "published" ? (
                <Link className="btn" href={`/projects/${project.id}`}>
                  Open the live listing
                </Link>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </>
  );
}
