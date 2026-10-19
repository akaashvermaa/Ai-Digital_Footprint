export default function Limitations({ items }) {
  if (!items || items.length === 0) return null
  return (
    <section className="block">
      <details className="limits">
        <summary>Limitations of this result</summary>
        <ul>
          {items.map((text) => <li key={text}>{text}</li>)}
        </ul>
      </details>
    </section>
  )
}
