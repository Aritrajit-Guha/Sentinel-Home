// Axios/fetch wrapper for calling the FastAPI backend
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function registerHousehold(payload) {
  const res = await fetch(`${BASE_URL}/api/households`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}
