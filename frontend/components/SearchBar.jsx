"use client";

import { useState } from "react";

// Kept in step with CATEGORIES in backend/schemas.py.
const CATEGORY_OPTIONS = [
  "web-app",
  "mobile-app",
  "ml-ai",
  "cli-tool",
  "library",
  "game",
  "data",
  "other",
];

export default function SearchBar({ onSearch, busy }) {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [tech, setTech] = useState("");
  const [maxPrice, setMaxPrice] = useState("");

  function submit(event) {
    event.preventDefault();
    onSearch({ q, category, tech, maxPrice });
  }

  return (
    <form className="search-strip" onSubmit={submit}>
      <label className="field search-input">
        <span className="field-label">Search</span>
        <input
          className="input"
          type="search"
          value={q}
          onChange={(event) => setQ(event.target.value)}
          placeholder="flashcards, attendance, python…"
        />
      </label>

      <label className="field">
        <span className="field-label">Category</span>
        <select className="select" value={category} onChange={(event) => setCategory(event.target.value)}>
          <option value="">Any</option>
          {CATEGORY_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span className="field-label">Tech</span>
        <input
          className="input"
          value={tech}
          onChange={(event) => setTech(event.target.value)}
          placeholder="React"
        />
      </label>

      <label className="field">
        <span className="field-label">Max price (₹)</span>
        <input
          className="input"
          type="number"
          min="0"
          value={maxPrice}
          onChange={(event) => setMaxPrice(event.target.value)}
          placeholder="500"
        />
      </label>

      <button className="btn btn-primary" type="submit" disabled={busy}>
        {busy ? "Searching…" : "Search"}
      </button>
    </form>
  );
}
