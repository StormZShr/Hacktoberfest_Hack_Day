// The A2 result. Advisory: the stamp is the model's opinion, so it is labelled
// as a check that ran here, and nothing here blocks a publish decision on its own.
export default function ReviewPanel({ review, busy, fresh }) {
  if (busy) {
    return (
      <div className="panel">
        <h3 className="panel-title">Quality check</h3>
        <p className="loading-note">Reading your listing with the local model. On CPU this takes a few seconds.</p>
      </div>
    );
  }

  if (!review) {
    return (
      <div className="panel">
        <h3 className="panel-title">Quality check</h3>
        <p className="row-meta">
          Not run yet. The check looks for missing setup steps, a licence, screenshots and tests, and
          it does not decide whether you can publish.
        </p>
      </div>
    );
  }

  return (
    <div className="panel">
      <h3 className="panel-title">Quality check</h3>

      <p className="review-score">
        <span className="stamp" data-fresh={fresh ? "true" : "false"}>
          <span className="stamp-label">Quality check</span>
          <span className="stamp-score">{review.score}/100</span>
          <span className="stamp-note">ran on this machine</span>
        </span>
      </p>

      <p className="review-summary">{review.summary}</p>

      {review.missing_items && review.missing_items.length > 0 ? (
        <ul className="missing">
          {review.missing_items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="ok-note">Nothing missing that the check could find.</p>
      )}

      {review.risk_flags && review.risk_flags.length > 0 ? (
        <ul className="flags">
          {review.risk_flags.map((flag) => (
            <li key={flag}>{flag}</li>
          ))}
        </ul>
      ) : null}

      {review.suggestions && review.suggestions.length > 0 ? (
        <>
          <p className="field-label">Fix next</p>
          <ul className="bullets">
            {review.suggestions.map((suggestion) => (
              <li key={suggestion}>{suggestion}</li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}
