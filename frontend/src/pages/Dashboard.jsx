import { useEffect, useState, useCallback } from 'react'
import { Link, useParams } from 'react-router-dom'
import { confirmSafe, getHouseholdStatus } from '../api/client'

function Score({ label, value, tone }) {
  return <div className="dashboard-score"><span>{label}</span><strong className={tone || ''}>{value ?? '—'}</strong></div>
}

function AlertCard({ alert, onConfirm, confirming }) {
  const confirmed = alert.status === 'confirmed'
  return <article className={`dashboard-alert ${confirmed ? 'alert-confirmed' : 'alert-active'}`}>
    <div className="dashboard-alert-head"><div><span className="dashboard-kicker">{alert.hazard || 'HAZARD'} · {alert.risk_level || 'ACTIVE'}</span><h3>{confirmed ? 'Household marked safe' : 'Action required now'}</h3></div><span className="dashboard-alert-status">{alert.status}</span></div>
    <p className="dashboard-alert-message">{alert.message}</p>
    <div className="dashboard-alert-meta"><span>Delivery: <b>{alert.delivery_status || 'pending'}</b></span><span>Channel: <b>{alert.delivery_channel || 'not sent'}</b></span></div>
    {alert.delivery_error && <p className="dashboard-warning">Delivery provider response: {alert.delivery_error}</p>}
    {alert.sources?.length > 0 && <details className="dashboard-details"><summary>View guidance sources</summary><ul>{alert.sources.map((source, index) => <li key={index}>{source.source || source.title || 'Guidance source'}{source.page ? ` · page ${source.page}` : ''}</li>)}</ul></details>}
    {!confirmed && <button className="dashboard-safe-button" onClick={onConfirm} disabled={confirming}>{confirming ? 'Updating safety status…' : '✓ I’m safe — stop escalation'}</button>}
  </article>
}

export default function Dashboard() {
  const { householdId } = useParams()
  const [status, setStatus] = useState(null), [error, setError] = useState(null), [confirming, setConfirming] = useState(false)
  const loadStatus = useCallback(async () => { try { setStatus(await getHouseholdStatus(householdId)); setError(null) } catch (err) { setError(err.message) } }, [householdId])
  useEffect(() => { loadStatus(); const timer = setInterval(loadStatus, 30000); return () => clearInterval(timer) }, [loadStatus])
  async function handleConfirm() { setConfirming(true); try { await confirmSafe(householdId); await loadStatus() } catch (err) { setError(err.message) } finally { setConfirming(false) } }
  if (error) return <main className="dashboard-shell"><div className="dashboard-error">{error}</div></main>
  if (!status) return <main className="dashboard-shell"><div className="dashboard-loading"><span className="live-dot" /> Connecting to SentinelHome monitoring…</div></main>
  const assessment = status.last_assessment || {}, active = status.active_alerts || []
  return <main className="dashboard-shell">
    <header className="dashboard-hero"><div><Link className="dashboard-back" to="/">← SentinelHome</Link><span className="dashboard-kicker">HOUSEHOLD COMMAND CENTER</span><h1>Your safety dashboard</h1><p>Live protection status, risk intelligence and response guidance for your household.</p></div><div className={`dashboard-monitor-pill ${status.safe ? 'monitor-safe' : 'monitor-alert'}`}><span className="live-dot" />{status.safe ? 'HOUSEHOLD SAFE' : 'MONITORING ACTIVE'}</div></header>
    <section className="dashboard-grid dashboard-overview"><article className="dashboard-glass dashboard-status-card"><div className="dashboard-card-title"><span>Current protection state</span><strong>{status.monitoring_state || 'monitoring'}</strong></div><div className="dashboard-risk-orb"><div><small>FINAL URGENCY</small><strong>{status.risk_score ?? '—'}</strong><span>{status.risk_level || 'not assessed'}</span></div></div><div className="dashboard-status-copy"><p>{status.safe ? 'Your household has confirmed safety. Escalation is paused.' : 'SentinelHome is watching for nearby hazards and will notify your configured contact.'}</p><small>Last update: {status.updated_at ? new Date(status.updated_at).toLocaleString() : 'live'}</small></div></article>
      <article className="dashboard-glass dashboard-intelligence"><div className="dashboard-card-title"><span>Latest intelligence</span><strong>{assessment.hazard || 'Earthquake model'}</strong></div><div className="dashboard-score-grid"><Score label="Damage grade" value={assessment.damage_grade} /><Score label="Physical risk" value={assessment.physical_damage_risk} tone="score-blue" /><Score label="Vulnerability" value={assessment.vulnerability_score} tone="score-purple" /><Score label="Urgency" value={assessment.urgency_score} tone="score-orange" /></div><div className="dashboard-progress"><span style={{ width: `${Math.max(0, Math.min(100, (Number(status.risk_score) || 0) * 100))}%` }} /></div><p className="dashboard-muted">Risk score is calculated from building damage, hazard severity and household vulnerability.</p></article></section>
    {active.length > 0 ? <section><div className="dashboard-section-heading"><span className="dashboard-kicker">RESPONSE CENTER</span><h2>Active alert{active.length > 1 ? 's' : ''}</h2></div>{active.map((alert) => <AlertCard alert={alert} onConfirm={handleConfirm} confirming={confirming} key={alert.id} />)}</section> : <section className="dashboard-glass dashboard-clear"><span className="clear-icon">✓</span><div><span className="dashboard-kicker">ALL CLEAR</span><h2>No active alerts</h2><p>Your household is currently being monitored. We’ll surface guidance here when a nearby event needs your attention.</p></div></section>}
    <section className="dashboard-section-heading recent-heading"><span className="dashboard-kicker">AUDIT TRAIL</span><h2>Recent activity</h2></section><div className="dashboard-glass dashboard-history">{(status.recent_alerts || []).length === 0 ? <p className="dashboard-muted">No previous alerts recorded.</p> : status.recent_alerts.map((alert) => <div className="history-row" key={alert.id}><span className="history-dot" /><div><b>{alert.hazard} response</b><p>{alert.status} · {alert.delivery_status || 'not delivered'}</p></div><small>{alert.created_at ? new Date(alert.created_at).toLocaleString() : ''}</small></div>)}</div>
  </main>
}
