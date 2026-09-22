import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { geocodeAddress, registerHousehold } from '../api/client'

const VULNERABLE_OPTIONS = ['children', 'elderly', 'disabled', 'pregnant', 'medical']

export default function Signup() {
  const navigate = useNavigate()
  const [address, setAddress] = useState('')
  const [locations, setLocations] = useState([])
  const [selectedLocation, setSelectedLocation] = useState(null)
  const [geocoding, setGeocoding] = useState(false)

  const [form, setForm] = useState({
    building_type: '',
    household_size: 1,
    emergency_contact: '',
    vulnerable_members: [],
  })

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  async function handleGeocode() {
    setError(null)
    setGeocoding(true)
    try {
      const result = await geocodeAddress(address)
      setLocations(result.locations)
      if (result.locations.length === 0) {
        setError('No matching locations found. Try a more specific address.')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setGeocoding(false)
    }
  }

  function toggleVulnerable(member) {
    setForm((prev) => {
      const has = prev.vulnerable_members.includes(member)
      return {
        ...prev,
        vulnerable_members: has
          ? prev.vulnerable_members.filter((m) => m !== member)
          : [...prev.vulnerable_members, member],
      }
    })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)

    if (!selectedLocation) {
      setError('Please search and select your location first.')
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        location: selectedLocation.display_name,
        latitude: selectedLocation.latitude,
        longitude: selectedLocation.longitude,
        building_type: form.building_type,
        household_size: Number(form.household_size),
        emergency_contact: form.emergency_contact,
        vulnerable_members: form.vulnerable_members,
      }
      const result = await registerHousehold(payload)
      navigate(`/dashboard/${result.household.id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main style={{ maxWidth: 560, margin: '0 auto', padding: '2rem' }}>
      <h1>Register your household</h1>
      <p>One-time setup. SentinelHome will watch hazard data for this location from now on.</p>

      <div style={{ marginBottom: '1.5rem' }}>
        <label>Address</label>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="e.g. Durgapur, West Bengal"
            style={{ flex: 1, padding: '0.5rem' }}
          />
          <button type="button" onClick={handleGeocode} disabled={geocoding || !address.trim()}>
            {geocoding ? 'Searching…' : 'Find location'}
          </button>
        </div>

        {locations.length > 0 && (
          <ul style={{ listStyle: 'none', padding: 0, marginTop: '0.75rem' }}>
            {locations.map((loc) => (
              <li key={`${loc.latitude}-${loc.longitude}`}>
                <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <input
                    type="radio"
                    name="location"
                    checked={selectedLocation?.latitude === loc.latitude && selectedLocation?.longitude === loc.longitude}
                    onChange={() => setSelectedLocation(loc)}
                  />
                  {loc.display_name}
                </label>
              </li>
            ))}
          </ul>
        )}
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '1rem' }}>
          <label>Building type</label>
          <select
            value={form.building_type}
            onChange={(e) => setForm({ ...form, building_type: e.target.value })}
            required
            style={{ width: '100%', padding: '0.5rem' }}
          >
            <option value="">Select…</option>
            <option value="ground_floor">Ground floor / independent house</option>
            <option value="apartment_low">Apartment (1-3 floors)</option>
            <option value="apartment_high">Apartment (4+ floors)</option>
          </select>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label>Number of people in household</label>
          <input
            type="number"
            min="1"
            value={form.household_size}
            onChange={(e) => setForm({ ...form, household_size: e.target.value })}
            required
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label>Emergency contact (phone number)</label>
          <input
            type="tel"
            value={form.emergency_contact}
            onChange={(e) => setForm({ ...form, emergency_contact: e.target.value })}
            placeholder="+91XXXXXXXXXX"
            required
            style={{ width: '100%', padding: '0.5rem' }}
          />
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <label>Vulnerable members in household (select all that apply)</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginTop: '0.5rem' }}>
            {VULNERABLE_OPTIONS.map((option) => (
              <label key={option} style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
                <input
                  type="checkbox"
                  checked={form.vulnerable_members.includes(option)}
                  onChange={() => toggleVulnerable(option)}
                />
                {option}
              </label>
            ))}
          </div>
        </div>

        {error && <p style={{ color: 'crimson' }}>{error}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? 'Registering…' : 'Register household'}
        </button>
      </form>
    </main>
  )
}