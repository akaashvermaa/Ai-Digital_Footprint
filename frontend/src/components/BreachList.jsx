import { useState } from 'react'

const SENSITIVE = ['Passwords', 'Phone numbers', 'Physical addresses', 'Dates of birth', 'Credit cards']

export default function BreachList({ breaches, status }) {
  const [showAll, setShowAll] = useState(false)
  const shown = showAll ? breaches : breaches.slice(0, 8)

  return (
    <section className="block">
      <h2>Data breaches <span className="count">{breaches.length}</span></h2>
      {status === 'unavailable' && (
        <p className="empty">The breach service could not be reached, so breaches are unknown, not zero. Try again later.</p>
      )}
      {status === 'ok' && breaches.length === 0 && <p className="empty">This email was not found in any known breach.</p>}
      {breaches.length > 0 && (
        <>
          <ul className="breaches">
            {shown.map((b) => (
              <li key={b.name}>
                <div className="breach-head">
                  <strong>{b.name}</strong>
                  <span className="muted small">{b.year}</span>
                </div>
                <div className="tags">
                  {b.data_exposed.map((d) => (
                    <span key={d} className={SENSITIVE.includes(d) ? 'tag tag-strong' : 'tag'}>{d}</span>
                  ))}
                </div>
              </li>
            ))}
          </ul>
          {breaches.length > 8 && (
            <p className="note">
              <button className="link-btn" onClick={() => setShowAll(!showAll)}>
                {showAll ? 'Show fewer' : `Show all ${breaches.length} breaches`}
              </button>
            </p>
          )}
        </>
      )}
    </section>
  )
}
