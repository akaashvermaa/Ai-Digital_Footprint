import { useRef, useState } from 'react'
import { analyze, downloadReport } from './api'
import BreachList from './components/BreachList'
import Breakdown from './components/Breakdown'
import FindingsList from './components/FindingsList'
import InputForm from './components/InputForm'
import Limitations from './components/Limitations'
import Recommendations from './components/Recommendations'
import ScoreSummary from './components/ScoreSummary'
import SitesFound from './components/SitesFound'

export default function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState('')
  const resultsRef = useRef(null)

  async function handleAnalyze(form) {
    setLoading(true)
    setError('')
    try {
      const data = await analyze(form)
      setResult(data)
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    } catch (e) {
      setError(e.message === 'Failed to fetch' ? 'Cannot reach the backend. Is it running on port 8000?' : e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleDownload() {
    setDownloading(true)
    try {
      await downloadReport(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="page">
      <header className="page-head">
        <h1>Digital Footprint Risk Analyzer</h1>
        <p>
          Enter a username, an email address or some text from a profile. The app checks what personal
          information is exposed and how to reduce it.
        </p>
      </header>

      <main>
        <InputForm onSubmit={handleAnalyze} loading={loading} />
        {error && <div className="error" role="alert"><strong>Error.</strong> {error}</div>}

        {result && (
          <section ref={resultsRef} className="results">
            <div className="results-head">
              <h2>Results</h2>
              <button className="btn btn-ghost" onClick={handleDownload} disabled={downloading}>
                {downloading ? 'Preparing PDF…' : 'Download PDF report'}
              </button>
            </div>

            <ScoreSummary score={result.score} level={result.level} summary={result.summary} />
            <Breakdown categories={result.categories} />
            {result.inputs.text && <FindingsList findings={result.findings} />}
            {result.inputs.username && (
              <SitesFound sites={result.sites_found} checked={result.sites_checked}
                          unknown={result.sites_unknown} status={result.username_check_status} />
            )}
            {result.inputs.email && <BreachList breaches={result.breaches} status={result.breach_check_status} />}
            <Recommendations items={result.recommendations} />
            <Limitations items={result.limitations} />
          </section>
        )}
      </main>

      <footer className="footer">
        Minor project. Nothing you enter is stored.
      </footer>
    </div>
  )
}
