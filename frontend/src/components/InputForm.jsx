import { useState } from 'react'

const EXAMPLE = {
  username: 'torvalds',
  email: 'test@example.com',
  text:
    "Hi I'm Rahul Sharma, call me at 9876543210, studying at IIT Kanpur. Born 12/05/2004.\n" +
    'Going to Goa with family for 2 weeks, house will be empty!\n' +
    'I leave the spare key under the doormat in case I forget mine.',
}

export default function InputForm({ onSubmit, loading }) {
  const [form, setForm] = useState({ username: '', email: '', text: '' })
  const [consent, setConsent] = useState(false)

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value })
  const hasInput = form.username.trim() || form.email.trim() || form.text.trim()

  function submit(e) {
    e.preventDefault()
    if (hasInput && consent && !loading) onSubmit(form)
  }

  return (
    <form className="form" onSubmit={submit}>
      <div className="form-head">
        <h2>Check a footprint</h2>
        <button type="button" className="link-btn" onClick={() => { setForm(EXAMPLE); setConsent(true) }}>
          Fill in an example
        </button>
      </div>

      <div className="form-row">
        <label className="field">
          <span>Username</span>
          <input type="text" value={form.username} onChange={update('username')} placeholder="akash_verma06" maxLength={40} />
          <small>Looked up on 62 public websites.</small>
        </label>
        <label className="field">
          <span>Email</span>
          <input type="email" value={form.email} onChange={update('email')} placeholder="you@example.com" maxLength={120} />
          <small>Checked against known data breaches.</small>
        </label>
      </div>

      <label className="field">
        <span>Bio or posts</span>
        <textarea
          value={form.text}
          onChange={update('text')}
          rows={5}
          maxLength={10000}
          placeholder="Paste a profile bio, a few posts or captions."
        />
        <small>Scanned for personal information and risky content.</small>
      </label>

      <div className="callout">
        <strong>Where your data goes.</strong> The username is checked on 62 public websites. The email is
        checked against a public breach database (XposedOrNot). The text is analysed only on this app&apos;s
        server. Nothing is stored. <strong>Never paste passwords or card numbers.</strong>
      </div>

      <label className="consent">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        <span>I am checking my own information, or I have permission to check it.</span>
      </label>

      <div className="form-actions">
        <button className="btn" disabled={!hasInput || !consent || loading}>
          {loading ? 'Analysing…' : 'Analyse'}
        </button>
      </div>
    </form>
  )
}
