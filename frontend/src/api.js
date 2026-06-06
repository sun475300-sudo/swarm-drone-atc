// SDACS FastAPI 백엔드(api/fastapi_server.py) 소비 클라이언트.
// 기본 경로는 상대 경로 → Vite proxy(dev) 또는 동일 출처(prod) 사용.
// VITE_API_BASE 로 직접 백엔드 주소를 지정할 수도 있다.

const BASE = import.meta.env.VITE_API_BASE || "";
const TOKEN_KEY = "sdacs_token";
const ROLE_KEY = "sdacs_role";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRole() {
  return localStorage.getItem(ROLE_KEY);
}

export function setSession(token, role) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(ROLE_KEY, role);
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
}

// FastAPI 응답 봉투({success, data} 또는 {detail})를 정규화한다.
async function request(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  let payload = null;
  try {
    payload = await res.json();
  } catch {
    payload = null;
  }

  if (!res.ok) {
    const detail = payload?.detail || payload?.error || `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return payload;
}

export async function login(username, password) {
  const data = await request("/auth/token", {
    method: "POST",
    body: { username, password },
  });
  setSession(data.access_token, data.role);
  return data;
}

export function getHealth() {
  return request("/health");
}

export async function listScenarios() {
  const data = await request("/api/scenarios");
  // {success, data: {id: meta, ...}} → [{id, ...meta}]
  const catalog = data?.data || {};
  return Object.entries(catalog).map(([id, meta]) => ({ id, ...meta }));
}

export async function runScenario(scenarioId, { seed = 42, durationS = null } = {}) {
  // 백엔드 RunScenarioBody.duration_s 는 정수 기본값(60) — null 은 생략한다.
  const body = { seed };
  if (durationS != null) body.duration_s = durationS;
  const data = await request(`/api/scenarios/${scenarioId}/run`, {
    method: "POST",
    auth: true,
    body,
  });
  return data.data; // {run_id, status, mode}
}

export async function getRun(runId) {
  const data = await request(`/api/runs/${runId}`);
  return data.data;
}

export async function getSnapshot() {
  const data = await request("/api/airspace/snapshot");
  return data.data; // {t, drones, conflicts}
}

// WebSocket 텔레메트리 구독. onMessage(parsed)·onStatus(string) 콜백.
// 반환된 close() 로 정리한다.
export function connectTelemetry({ onMessage, onStatus }) {
  const base = BASE || window.location.origin;
  // http://→ws://, https://→wss:// (단순 /^http/ 치환은 https 에서 깨짐)
  const wsUrl = base.replace(/^http(s)?:\/\//, "ws$1://") + "/ws/telemetry";
  const ws = new WebSocket(wsUrl);
  ws.onopen = () => onStatus?.("connected");
  ws.onclose = () => onStatus?.("disconnected");
  ws.onerror = () => onStatus?.("error");
  ws.onmessage = (ev) => {
    try {
      onMessage?.(JSON.parse(ev.data));
    } catch {
      /* 비 JSON 프레임 무시 */
    }
  };
  return () => ws.close();
}
