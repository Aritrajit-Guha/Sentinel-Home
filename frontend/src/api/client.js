const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = data.errors ? data.errors.join(", ") : data.message || "Request failed";
    throw new Error(message);
  }
  return data;
}

// Households
export function geocodeAddress(address) {
  return request(`/api/households/geocode?address=${encodeURIComponent(address)}`);
}

export function registerHousehold(payload) {
  return request("/api/households", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getHousehold(householdId) {
  return request(`/api/households/${householdId}`);
}

export function getHouseholdStatus(householdId) {
  return request(`/api/households/${householdId}/status`);
}

export function getHouseholdEarthquakes(householdId, radiusKm = 500) {
  return request(`/api/households/${householdId}/hazards/earthquakes?radius_km=${radiusKm}`);
}

export function getHouseholdWeather(householdId) {
  return request(`/api/households/${householdId}/hazards/weather`);
}

// Alerts
export function getHouseholdAlerts(householdId) {
  return request(`/api/alerts/${householdId}`);
}

export function confirmSafe(householdId) {
  return request(`/api/alerts/${householdId}/confirm-safe`, { method: "POST" });
}