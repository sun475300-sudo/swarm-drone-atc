// SDACS FastAPI 백엔드용 타입 클라이언트.
// 응답 봉투({success,data})를 해제하고 실패 시 명시적으로 throw 한다.

import type {
  Envelope,
  RunRecordData,
  RunScenarioBody,
  RunStartData,
  ScenarioCatalog,
  SnapshotData,
} from "./types";

// 개발 시 VITE_API_BASE 미설정이면 FastAPI 기본 포트(8000)를 가리킨다.
const API_BASE: string =
  (import.meta.env?.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** {success,data} 봉투를 해제한다. 실패하면 ApiError 를 던진다. */
export function unwrap<T>(body: Envelope<T>, status: number): T {
  if (!body.success || body.data === undefined || body.data === null) {
    throw new ApiError(body.error ?? `request failed (HTTP ${status})`, status);
  }
  return body.data;
}

/** res.json() 을 안전하게 파싱한다. 비-JSON(uvicorn 500 등)은 ApiError 로 변환. */
async function parseEnvelope<T>(res: Response): Promise<Envelope<T>> {
  try {
    return (await res.json()) as Envelope<T>;
  } catch {
    throw new ApiError(`HTTP ${res.status} (non-JSON response)`, res.status);
  }
}

async function getJson<T>(path: string, token?: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  return unwrap(await parseEnvelope<T>(res), res.status);
}

export function fetchScenarios(): Promise<ScenarioCatalog> {
  return getJson<ScenarioCatalog>("/api/scenarios");
}

export function fetchSnapshot(): Promise<SnapshotData> {
  return getJson<SnapshotData>("/api/airspace/snapshot");
}

export function fetchRun(runId: string): Promise<RunRecordData> {
  return getJson<RunRecordData>(`/api/runs/${encodeURIComponent(runId)}`);
}

/** 시나리오 실행 트리거. Bearer 토큰 필수(require_token). */
export async function startRun(
  scenarioId: string,
  body: RunScenarioBody,
  token: string,
): Promise<RunStartData> {
  const res = await fetch(
    `${API_BASE}/api/scenarios/${encodeURIComponent(scenarioId)}/run`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    },
  );
  return unwrap(await parseEnvelope<RunStartData>(res), res.status);
}

/** WebSocket 텔레메트리 엔드포인트의 절대 URL(http→ws 변환). */
export function telemetryWsUrl(): string {
  const base = API_BASE.replace(/^http/, "ws");
  return `${base}/ws/telemetry`;
}
