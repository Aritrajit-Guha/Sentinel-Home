import { useState } from 'react'
import { Link } from 'react-router-dom'
import { confirmSafe, getEarthquakeSimulation, startEarthquakeSimulation } from '../api/client'

const stageLabels = {
  hazard_api: 'Hazard API', parameter_generation: 'LLM parameter generation',
  ml_inference: 'ML inference', rag_retrieval: 'RAG retrieval',
  guidance_generation: 'LLM safety guidance', alert_persistence: 'Alert persistence',
  notification: 'Telegram delivery', confirmation: 'Confirmation monitor', escalation: 'Escalation',
}

function JsonBlock({ label, value }) {
  if (value === undefined || value === null) return null
  return <details className="trace-data"><summary>{label}</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>
}

function TraceEvent({ event }) {
  return <article className={`trace-event trace-${event.status || 'running'}`}>
    <div className="trace-marker" /><div className="trace-event-body">
      <div className="trace-event-heading"><span className="trace-stage">{stageLabels[event.stage] || event.stage}</span><span className="trace-status">{event.status || 'running'}</span></div>
      <strong>{event.title}</strong>{event.detail && <p>{event.detail}</p>}
      <div className="trace-event-meta">{event.household_id && `Household ${event.household_id.slice(0, 8)} · `}{event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : 'just now'}</div>
      <div className="trace-data-row"><JsonBlock label="Request / prompt" value={event.request} /><JsonBlock label="Response" value={event.response} /></div>
      {event.error && <pre className="trace-error">{event.error}</pre>}
    </div>
  </article>
}

function Metric({ label, value, accent }) {
  return <div className={`simulation-metric ${accent || ''}`}><span>{label}</span><strong>{value ?? '—'}</strong></div>
}

function HouseholdCard({ item, onConfirm }) {
  const assessment = item.assessment || {}, advice = item.advice || {}, alert = item.alert || {}
  const canConfirm = alert.id && ['active', 'escalation_pending', 'pending'].includes(alert.status) && item.confirmation_status !== 'confirmed'
  return <article className="glass-card household-card">
    <div className="household-heading"><div><span className="eyebrow">HOUSEHOLD NODE</span><h3>{item.household_id}</h3></div><span className={`risk-pill risk-${assessment.urgency_level || 'unknown'}`}>{assessment.urgency_level || 'unknown'}</span></div>
    <div className="metric-grid"><Metric label="Damage grade" value={assessment.damage_grade} /><Metric label="Urgency score" value={assessment.urgency_score} accent="accent-blue" /><Metric label="Physical risk" value={assessment.physical_damage_risk} /><Metric label="Vulnerability" value={assessment.vulnerability_score} /></div>
    <div className="household-status-row"><span>Confirmation: <b>{item.confirmation_status || 'not required'}</b></span><span>Escalation: <b>{item.escalation_required ? 'required' : 'not required'}</b></span></div>
    {advice.message && <section className="advice-panel"><div className="section-title"><span className="live-dot" /> Safety guidance</div>
      {advice.degraded && <p className="warning-text">Generation degraded: {advice.generation_error || 'provider did not return guidance'}</p>}
      <p className="guidance-message">{advice.message}</p>
      {advice.retrieved_guidance?.length > 0 && <details className="source-detail"><summary>Retrieved guidance excerpts ({advice.retrieved_guidance.length})</summary>{advice.retrieved_guidance.map((doc, index) => <div className="excerpt" key={index}><b>{doc.source}{doc.page ? ` · page ${doc.page}` : ''}</b><p>{doc.excerpt}</p></div>)}</details>}
      <details className="source-detail"><summary>Inspect LLM prompt and sources</summary><JsonBlock label="Prompt sent to guidance model" value={advice.prompt} /><ul className="source-list">{(advice.sources || []).map((source, index) => <li key={index}>{source.source || source.title || 'Guidance source'}{source.page ? ` · page ${source.page}` : ''}</li>)}</ul></details>
    </section>}
    {alert.id && <section className="alert-panel"><div><span className="section-title">Alert channel</span><span className={`delivery-state ${alert.delivery_status}`}>{alert.delivery_channel || 'notification'} · {alert.delivery_status || alert.status}</span></div>
      {alert.delivery_error && <p className="warning-text">Provider response: {alert.delivery_error}</p>}{alert.delivery_id && <small>Provider message ID: {alert.delivery_id}</small>}
      {canConfirm && <button className="safe-button" onClick={() => onConfirm(item.household_id)}>✓ I’m safe — stop escalation</button>}
      {item.confirmation_status === 'confirmed' && <p className="confirmed-text">✓ Safety confirmed. Further escalation is stopped.</p>}
      <Link className="dashboard-link" to={`/dashboard/${item.household_id}`}>Open household dashboard →</Link>
    </section>}
  </article>
}

export default function Simulation() {
  const [password, setPassword] = useState(''), [result, setResult] = useState(null), [events, setEvents] = useState([]), [error, setError] = useState(null), [running, setRunning] = useState(false)
  async function handleSubmit(event) {
    event.preventDefault(); setRunning(true); setError(null); setResult(null); setEvents([{ stage: 'hazard_api', status: 'running', title: 'Submitting controlled earthquake fixture', detail: 'The backend is accepting the protected simulation request.' }])
    try {
      let job = await startEarthquakeSimulation(password); setEvents(job.events || [])
      while (job.status === 'queued' || job.status === 'running') { await new Promise((resolve) => setTimeout(resolve, 900)); job = await getEarthquakeSimulation(job.job_id); setEvents(job.events || []) }
      if (job.status === 'failed') throw new Error(job.error || 'Simulation failed')
      setEvents(job.events || []); setResult({ ...job, ...job.result }); setPassword('')
    } catch (err) { setError(err.message) } finally { setRunning(false) }
  }
  async function handleConfirm(householdId) {
    try { await confirmSafe(householdId); setResult((current) => current && ({ ...current, households: current.households.map((item) => item.household_id === householdId ? { ...item, confirmation_status: 'confirmed', escalation_required: false, alert: { ...item.alert, status: 'confirmed' } } : item) })); setEvents((current) => [...current, { stage: 'confirmation', status: 'completed', title: 'Household confirmed safe', detail: 'The active alert was confirmed from the developer dashboard.' }]) }
    catch (err) { setError(err.message) }
  }
  return <main className="simulation-shell">
    <section className="simulation-hero"><div><span className="eyebrow">SENTINELHOME · INTERNAL CONTROL ROOM</span><h1>Earthquake response engine</h1><p>Watch the complete detection, intelligence, guidance and notification pipeline execute in real time.</p></div><div className={`engine-state ${running ? 'state-running' : result ? 'state-complete' : ''}`}><span className="live-dot" />{running ? 'ENGINE RUNNING' : result ? 'RUN COMPLETE' : 'ENGINE STANDBY'}</div></section>
    <section className="glass-card simulation-control"><div><span className="eyebrow">CONTROLLED FIXTURE</span><h2>Launch workflow</h2><p>Protected simulation only. The password is never included in the trace.</p></div><form onSubmit={handleSubmit}><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Simulation password" required autoComplete="current-password" /><button type="submit" disabled={running}>{running ? 'Processing…' : 'Run simulation →'}</button></form></section>
    {error && <div className="simulation-error">{error}</div>}
    {(running || events.length > 0) && <section className="glass-card trace-panel"><div className="panel-heading"><div><span className="eyebrow">LIVE TELEMETRY</span><h2>Engine trace</h2></div><span>{events.length} events</span></div><div className="simulation-timeline">{events.map((event, index) => <TraceEvent event={event} key={`${event.timestamp || 'local'}-${event.stage}-${index}`} />)}</div></section>}
    {result && <><section className="simulation-summary"><Metric label="Event" value={result.simulation_event_id} /><Metric label="Households checked" value={result.households_checked} /><Metric label="Nearby households" value={result.households_with_nearby_earthquakes} /></section><section className="household-list">{result.households?.map((item) => <HouseholdCard item={item} onConfirm={handleConfirm} key={item.household_id} />)}</section></>}
  </main>
}
