"use client";

// Kept in step with CATEGORIES and DIFFICULTIES in backend/schemas.py.
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
const DIFFICULTY_OPTIONS = ["beginner", "intermediate", "advanced"];

function linesToArray(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

// The listing fields the seller edits after autofill. Plain textareas for the
// list fields: one item per line, which is faster to fix than a chip editor.
export default function ListingForm({ listing, onChange }) {
  function set(field, value) {
    onChange({ ...listing, [field]: value });
  }

  return (
    <div>
      <label className="field">
        <span className="field-label">Title</span>
        <input
          className="input"
          value={listing.title || ""}
          maxLength={120}
          onChange={(event) => set("title", event.target.value)}
        />
      </label>

      <label className="field">
        <span className="field-label">Tagline</span>
        <input
          className="input"
          value={listing.tagline || ""}
          maxLength={200}
          onChange={(event) => set("tagline", event.target.value)}
        />
      </label>

      <label className="field">
        <span className="field-label">Description</span>
        <textarea
          className="textarea"
          value={listing.description || ""}
          onChange={(event) => set("description", event.target.value)}
        />
      </label>

      <label className="field">
        <span className="field-label">Tech stack</span>
        <input
          className="input"
          value={(listing.tech_stack || []).join(", ")}
          onChange={(event) =>
            set(
              "tech_stack",
              event.target.value
                .split(",")
                .map((item) => item.trim())
                .filter(Boolean)
            )
          }
          placeholder="Python, FastAPI, SQLite"
        />
        <p className="hint">Separate with commas.</p>
      </label>

      <label className="field">
        <span className="field-label">Category</span>
        <select
          className="select"
          value={listing.category || ""}
          onChange={(event) => set("category", event.target.value)}
        >
          <option value="">Pick one</option>
          {CATEGORY_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span className="field-label">Difficulty</span>
        <select
          className="select"
          value={listing.difficulty || ""}
          onChange={(event) => set("difficulty", event.target.value)}
        >
          <option value="">Pick one</option>
          {DIFFICULTY_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span className="field-label">What the buyer gets</span>
        <textarea
          className="textarea"
          value={(listing.what_you_get || []).join("\n")}
          onChange={(event) => set("what_you_get", linesToArray(event.target.value))}
          placeholder={"Full source code\nSetup steps in the README\nSample data"}
        />
        <p className="hint">One item per line.</p>
      </label>

      <label className="field">
        <span className="field-label">Demo talking points</span>
        <textarea
          className="textarea"
          value={(listing.demo_points || []).join("\n")}
          onChange={(event) => set("demo_points", linesToArray(event.target.value))}
          placeholder={"Paste a page of notes and flashcards appear\nWrong answers come back next round"}
        />
        <p className="hint">One line per point.</p>
      </label>

      <label className="field">
        <span className="field-label">Price in rupees</span>
        <input
          className="input"
          type="number"
          min="0"
          value={listing.price_inr ?? 0}
          onChange={(event) => set("price_inr", Number(event.target.value))}
        />
      </label>

      <label className="field">
        <span className="field-label">Demo link</span>
        <input
          className="input"
          value={listing.demo_url || ""}
          onChange={(event) => set("demo_url", event.target.value)}
          placeholder="https://github.com/you/project"
        />
      </label>
    </div>
  );
}
