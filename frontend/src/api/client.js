const BASE = "/api";

function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function login(username, password) {
  const res = await fetch(`${BASE}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error("Login failed");
  return res.json(); // { access_token, token_type }
}

export async function fetchSnapshot(token) {
  const res = await fetch(`${BASE}/airspace/snapshot`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error("Snapshot fetch failed");
  return res.json();
}

export async function fetchScenarios(token) {
  const res = await fetch(`${BASE}/scenarios`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error("Scenarios fetch failed");
  return res.json();
}

export async function runScenario(token, scenarioId) {
  const res = await fetch(`${BASE}/scenarios/${scenarioId}/run`, {
    method: "POST",
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error("Scenario run failed");
  return res.json(); // { run_id }
}

export async function fetchRun(token, runId) {
  const res = await fetch(`${BASE}/runs/${runId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error("Run fetch failed");
  return res.json();
}

export async function fetchAuditLog(token, { limit = 50 } = {}) {
  const res = await fetch(`${BASE}/audit-log?limit=${limit}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error("Audit log fetch failed");
  return res.json();
}

export function connectTelemetry(token, onMessage) {
  const url = new URL("/ws/telemetry", window.location.href);
  url.protocol = url.protocol.replace("http", "ws");
  if (token) url.searchParams.set("token", token);

  const ws = new WebSocket(url.toString());
  ws.onmessage = (e) => {
    try {
      onMessage(JSON.parse(e.data));
    } catch {
      // ignore malformed frames
    }
  };
  return ws;
}
