import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getEarthquakeSimulation, startEarthquakeSimulation } from '../api/client'

export default function Simulation() {
  const [password, setPassword] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [running, setRunning] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setRunning(true)
    setError(null)
    setResult(null)
    try {
      const accepted = await startEarthquakeSimulation(password)
      let job = accepted
      while (job.status === 'queued' || job.status === 'running') {
        await new Promise((resolve) => setTimeout(resolve, 3000))
        job = await getEarthquakeSimulation(accepted.job_id)
      }
      if (job.status === 'failed') throw new Error(job.error || 'Simulation failed')
      setResult({ ...job, ...job.result })
      setPassword('')
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <main style={{ maxWidth: 760, margin: '0 auto', padding: '2rem' }}>
      <h1>Controlled earthquake simulation</h1>
      <p>Enter the private simulation password to run the full SentinelHome workflow.</p>
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.75rem', margin: '1.5rem 0' }}>
        <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Simulation password" required autoComplete="current-password" style={{ flex: 1, padding: '0.75rem' }} />
        <button type="submit" disabled={running}>{running ? 'Running…' : 'Run simulation'}</button>
      </form>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      {result && (
        <section>
          <h2>Simulation result</h2>
          <p><strong>Event:</strong> {result.simulation_event_id}</p>
          <p><strong>Households checked:</strong> {result.households_checked}</p>
          <p><strong>Households with nearby event:</strong> {result.households_with_nearby_earthquakes}</p>
          {result.households?.map((household) => (
            <article key={household.household_id} style={{ border: '1px solid #ccc', borderRadius: 8, padding: '1rem', marginTop: '1rem' }}>
              <h3>Household {household.household_id}</h3>
              <p><strong>Confirmation:</strong> {household.confirmation_status || 'not required'}</p>
              <p><strong>Escalation required:</strong> {household.escalation_required ? 'Yes' : 'No'}</p>
              {household.assessment && <>
                <p><strong>Damage grade:</strong> {household.assessment.damage_grade ?? 'Unavailable'}</p>
                <p><strong>Urgency:</strong> {household.assessment.urgency_level} ({household.assessment.urgency_score})</p>
                <p><strong>Physical damage risk:</strong> {household.assessment.physical_damage_risk}</p>
                <p><strong>Vulnerability score:</strong> {household.assessment.vulnerability_score}</p>
              </>}
              {household.advice && <>
                <h4>Safety instructions</h4>
                {household.advice.degraded && <p style={{ color: '#8a5a00' }}>
                  Guidance generation is temporarily unavailable. A conservative fallback message is shown; follow local-authority instructions.
                </p>}
                <p>{household.advice.message}</p>
                <h4>Sources</h4>
                <ul>{(household.advice.sources || []).map((source, index) => <li key={index}>{source.source || source.title || 'Guidance source'}{source.page ? `, page ${source.page}` : ''}</li>)}</ul>
              </>}
              {household.alert && <>
                <p><strong>Alert:</strong> {household.alert.status} — delivery {household.alert.delivery_status || 'pending'}</p>
                {household.alert.delivery_error && <p style={{ color: '#8a5a00' }}>
                  Delivery issue: the alert was saved, but the provider reported an error. Verify the recipient number in Twilio.
                </p>}
                <Link to={`/dashboard/${household.household_id}`}>Open household dashboard</Link>
              </>}
            </article>
          ))}
        </section>
      )}
    </main>
  )
}
