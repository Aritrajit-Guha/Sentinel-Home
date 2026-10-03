import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { getHouseholdStatus, confirmSafe } from '../api/client'

export default function Dashboard() {
  const { householdId } = useParams()
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)
  const [confirming, setConfirming] = useState(false)

  const loadStatus = useCallback(async () => {
    try {
      const result = await getHouseholdStatus(householdId)
      setStatus(result)
      setError(null)
    } catch (err) {
      setError(err.message)
    }
  }, [householdId])

  useEffect(() => {
    loadStatus()
    const interval = setInterval(loadStatus, 30000) // poll every 30s
    return () => clearInterval(interval)
  }, [loadStatus])

  async function handleConfirmSafe() {
    setConfirming(true)
    try {
      await confirmSafe(householdId)
      await loadStatus()
    } catch (err) {
      setError(err.message)
    } finally {
      setConfirming(false)
    }
  }

  if (error) return <main style={{ padding: '2rem' }}><p style={{ color: 'crimson' }}>{error}</p></main>
  if (!status) return <main style={{ padding: '2rem' }}><p>Loading…</p></main>

  return (
    <main style={{ maxWidth: 560, margin: '0 auto', padding: '2rem' }}>
      <h1>Household status</h1>

      <div style={{ padding: '1rem', border: '1px solid #ddd', borderRadius: 8, marginBottom: '1rem' }}>
        <p><strong>Monitoring state:</strong> {status.monitoring_state}</p>
        <p><strong>Risk level:</strong> {status.risk_level}</p>
        <p><strong>Risk score:</strong> {status.risk_score ?? 'Not yet assessed'}</p>
        <p><strong>Safe:</strong> {status.safe ? 'Yes' : 'No — awaiting confirmation'}</p>
      </div>

      {status.last_assessment && (
        <section style={{ padding: '1rem', border: '1px solid #ddd', borderRadius: 8, marginBottom: '1rem' }}>
          <h2>Latest assessment</h2>
          <p><strong>Damage grade:</strong> {status.last_assessment.damage_grade ?? 'Unavailable'}</p>
          <p><strong>Physical damage risk:</strong> {status.last_assessment.physical_damage_risk ?? 'Unavailable'}</p>
          <p><strong>Vulnerability score:</strong> {status.last_assessment.vulnerability_score ?? 'Unavailable'}</p>
          <p><strong>Final urgency:</strong> {status.last_assessment.urgency_score ?? 'Unavailable'} ({status.last_assessment.urgency_level ?? 'unknown'})</p>
        </section>
      )}

      {status.active_alerts.length > 0 && (
        <div style={{ padding: '1rem', border: '1px solid crimson', borderRadius: 8, marginBottom: '1rem' }}>
          <h2>Active alerts</h2>
          {status.active_alerts.map((alert) => (
            <div key={alert.id}>
              <p><strong>{alert.hazard}</strong>: {alert.message}</p>
              <p><strong>Delivery:</strong> {alert.delivery_status || 'pending'} ({alert.delivery_channel || 'not sent'})</p>
              {alert.sources?.length > 0 && (
                <details>
                  <summary>Guidance sources</summary>
                  <ul>{alert.sources.map((source, index) => <li key={index}>{source.source || source.title || 'Guidance source'}{source.page ? `, page ${source.page}` : ''}</li>)}</ul>
                </details>
              )}
            </div>
          ))}
          <button onClick={handleConfirmSafe} disabled={confirming}>
            {confirming ? 'Confirming…' : "I'm safe"}
          </button>
        </div>
      )}

      <h2>Recent alerts</h2>
      {status.recent_alerts.length === 0 ? (
        <p>No alerts yet.</p>
      ) : (
        <ul>
          {status.recent_alerts.map((alert) => (
            <li key={alert.id}>{alert.hazard} — {alert.status} — {alert.message}</li>
          ))}
        </ul>
      )}
    </main>
  )
}
