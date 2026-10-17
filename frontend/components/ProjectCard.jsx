import Link from "next/link";

// A pinned index card: tape strip, title, tagline, tech, price tag, and the
// AI quality stamp in the corner (the one loud element on the board).
export default function ProjectCard({ project }) {
  const hasScore = project.ai_score !== null && project.ai_score !== undefined;

  return (
    <article className="card">
      <h2 className="card-title">
        <Link href={`/projects/${project.id}`}>{project.title || "Untitled draft"}</Link>
      </h2>
      <p className="card-tagline">{project.tagline || "No tagline written yet."}</p>

      {project.tech_stack && project.tech_stack.length > 0 ? (
        <p className="card-tech">{project.tech_stack.join(", ")}</p>
      ) : null}

      <div className="card-foot">
        {hasScore ? (
          <span className="stamp">
            <span className="stamp-label">Quality check</span>
            <span className="stamp-score">{project.ai_score}/100</span>
            <span className="stamp-note">ran on this machine</span>
          </span>
        ) : null}
        {project.status === "draft" ? <span className="draft-note">Draft</span> : null}
        <span className="price-tag">₹{project.price_inr}</span>
      </div>
    </article>
  );
}
