// Small wrapper around the backend API (Vite proxies /api to localhost:8000)

async function errorMessage(res) {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // response was not JSON
  }
  return `Request failed (${res.status})`
}

export async function analyze(payload) {
  const res = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await errorMessage(res))
  return res.json()
}

export async function downloadReport(result) {
  const res = await fetch('/api/report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(result),
  })
  if (!res.ok) throw new Error(await errorMessage(res))

  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = 'footprint-risk-report.pdf'
  a.click()
  URL.revokeObjectURL(url)
}
