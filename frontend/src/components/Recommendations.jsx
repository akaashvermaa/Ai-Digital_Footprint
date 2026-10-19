const GROUPS = [
  { key: 'urgent', title: 'Do this first' },
  { key: 'important', title: 'Important' },
  { key: 'good practice', title: 'Good practice' },
]

export default function Recommendations({ items }) {
  let step = 0
  return (
    <section className="block">
      <h2>What to do next</h2>
      {GROUPS.map(({ key, title }) => {
        const group = items.filter((r) => r.priority === key)
        if (group.length === 0) return null
        return (
          <div key={key} className="advice-group">
            <h3>{title}</h3>
            <ol className="advice">
              {group.map((r) => (
                <li key={r.text}>
                  <span className="step">{++step}.</span>
                  <span>{r.text}</span>
                </li>
              ))}
            </ol>
          </div>
        )
      })}
    </section>
  )
}
