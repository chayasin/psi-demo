const API_BASE = "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export function getStatus() {
  return request("/api/status");
}

export function resetSession() {
  return request("/api/reset", { method: "POST" });
}

export function generateData() {
  return request("/api/generate-data", { method: "POST" });
}

export function runPSI() {
  return request("/api/run-psi", { method: "POST" });
}

export function runJoin() {
  return request("/api/run-join", { method: "POST" });
}

export function runInsecureAggregation() {
  return request("/api/run-insecure-aggregation", { method: "POST" });
}

export function runSecureAggregation() {
  return request("/api/run-secure-aggregation", { method: "POST" });
}

export function getLogs() {
  return request("/api/logs");
}
