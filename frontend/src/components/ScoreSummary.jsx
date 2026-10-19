// The overall number, its level, and a plain list of what was discovered.
export default function ScoreSummary({ score, level, summary }) {
  return (
    <section className="score-block">
      <div>
        <div>
          <span className="score-num">{score}</span>
          <span className="score-max">/ 100</span>
        </div>
        <p className="score-level">
          <span className={`tag tag-${level.toLowerCase()}`}>{level} risk</span>
        </p>
      </div>
      <div>
        <h3>What was found</h3>
        <ul className="plain-list">
          {summary.map((line) => <li key={line}>{line}</li>)}
        </ul>
      </div>
    </section>
  )
}
