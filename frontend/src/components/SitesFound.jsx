export default function SitesFound({ sites, checked, unknown, status }) {
  return (
    <section className="block">
      <h2>Accounts found <span className="count">{sites.length} of {checked + unknown} sites</span></h2>
      {status === 'unavailable' ? (
        <p className="empty">No site could be checked, so this is unknown, not zero.</p>
      ) : sites.length === 0 ? (
        <p className="empty">This username was not found on any of the sites checked.</p>
      ) : (
        <>
          <div className="tags">
            {sites.map((s) => (
              <a key={s.site} href={s.url} target="_blank" rel="noreferrer" className="tag">{s.site}</a>
            ))}
          </div>
          <p className="muted small note">
            Anyone can link these profiles because they share one username. A match may belong to a
            different person with the same name.
          </p>
        </>
      )}
      {unknown > 0 && status !== 'unavailable' && (
        <p className="muted small note">{unknown} sites could not be checked (blocked or timed out), so more accounts may exist.</p>
      )}
    </section>
  )
}
