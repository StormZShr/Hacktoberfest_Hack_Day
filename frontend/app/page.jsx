"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import ProjectCard from "../components/ProjectCard";
import SearchBar from "../components/SearchBar";
import { listProjects } from "../lib/api";

export default function BoardPage() {
  const [projects, setProjects] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  const load = useCallback(async (filters = {}) => {
    setBusy(true);
    setError("");
    try {
      setProjects(await listProjects(filters));
    } catch (err) {
      setError(err.message);
      setProjects([]);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <SearchBar
        busy={busy}
        onSearch={(filters) => {
          setSearched(true);
          load(filters);
        }}
      />

      {error ? <p className="error-note">{error}</p> : null}
      {busy && !projects ? <p className="loading-note">Loading the board…</p> : null}

      {projects && projects.length === 0 ? (
        <div className="empty">
          <p className="empty-title">
            {searched ? "No projects match those filters." : "No projects on the board yet."}
          </p>
          <p className="row-meta">
            {searched
              ? "Try a higher price, or clear the tech filter."
              : "The board fills up as sellers list their projects."}
          </p>
          <Link className="btn btn-primary" href="/sell/new">
            List a project
          </Link>
        </div>
      ) : null}

      <div className="board">
        {(projects || []).map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </>
  );
}
