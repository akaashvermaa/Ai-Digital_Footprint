const ORDER = { high: 0, medium: 1, low: 2 }

export default function FindingsList({ findings }) {
  const sorted = [...findings].sort((a, b) => ORDER[a.severity] - ORDER[b.severity])

  return (
    <section className="block">
      <h2>Findings in the text <span className="count">{findings.length}</span></h2>
      {sorted.length === 0 ? (
        <p className="empty">No personal information or risky content was detected.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Finding</th>
              <th>Why it matters</th>
              <th>What to do</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((f, i) => (
              <tr key={i}>
                <td className="sev"><span className={`tag tag-${f.severity}`}>{f.severity}</span></td>
                <td data-label="Finding">
                  <div className="finding-value">{f.value}</div>
                  <div className="finding-meta">
                    {f.type.replace(/ \(\d+% confidence\)/, '')}{f.occurrences > 1 ? `, found ${f.occurrences} times` : ''}
                    <br />
                    {Math.round(f.confidence * 100)}% sure · {f.source}
                  </div>
                </td>
                <td data-label="Why it matters">{f.explanation}</td>
                <td data-label="What to do">{f.fix}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
