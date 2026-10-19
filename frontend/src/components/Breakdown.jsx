// One row per category. Open a row to see exactly which findings produced its points.
function valueText(c) {
  if (c.checked) return `${c.score} / 100`
  return c.status === 'unavailable' ? 'Could not check' : 'Not checked'
}

export default function Breakdown({ categories }) {
  return (
    <section className="block">
      <h2>Score breakdown</h2>
      <div className="rows">
        {categories.map((c) => (
          <details key={c.key} className="row">
            <summary>
              <span>{c.label}</span>
              <span className="bar"><span className="bar-fill" style={{ width: `${c.checked ? c.score : 0}%` }} /></span>
              <span className={`row-value${c.checked ? '' : ' off'}`}>{valueText(c)}</span>
            </summary>
            <div className="row-detail">
              {!c.checked && (
                <p className="muted">
                  {c.status === 'unavailable'
                    ? 'This check failed, so it is left out of the total instead of counting as zero.'
                    : 'Not requested, so it is left out of the total.'}
                </p>
              )}
              {c.checked && c.contributions.length === 0 && <p className="muted">Nothing found, so no points.</p>}
              {c.checked && c.contributions.length > 0 && (
                <>
                  <ul>
                    {c.contributions.map((x) => (
                      <li key={x.label}><span>{x.label}</span><span>+{x.points}</span></li>
                    ))}
                  </ul>
                  <p className="muted small note">Counts for {Math.round(c.weight * 100)}% of the overall score.</p>
                </>
              )}
            </div>
          </details>
        ))}
      </div>
      <p className="muted small note">Select a row to see where its points come from.</p>
    </section>
  )
}
