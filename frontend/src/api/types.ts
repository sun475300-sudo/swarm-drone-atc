// FastAPI 백엔드(api/fastapi_server.py)의 응답 스키마를 미러링한 타입.
// 모든 /api/* 응답은 { success, data } 또는 { success:false, error } 봉투를 따른다.

export interface Envelope<T> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface ScenarioMeta {
  name: string;
  difficulty?: string;
  source?: string;
  n_drones?: number;
}

export type ScenarioCatalog = Record<string, ScenarioMeta>;

export interface SnapshotData {
  t: number; // timestamp_ns
  drones: unknown[];
  conflicts: unknown[];
}

export type RunStatus = "queued" | "running" | "completed" | "failed";

export interface RunStartData {
  run_id: string;
  status: RunStatus;
  mode: "scenario" | "live_airspace";
}

export interface RunRecordData {
  run_id: string;
  scenario_id: string;
  status: RunStatus;
  started_at_ns: number;
  finished_at_ns: number | null;
  metrics: Record<string, unknown>;
}

// POST /api/scenarios/{id}/run 바디 (RunScenarioBody)
export interface RunScenarioBody {
  seed: number;
  method: "orca" | "apf" | "cbs" | "hybrid";
  duration_s: number;
}

// WebSocket /ws/telemetry 가 브로드캐스트하는 이벤트(느슨한 형태).
export interface TelemetryEvent {
  type?: string;
  t?: number;
  drones?: unknown[];
  conflicts?: unknown[];
  [key: string]: unknown;
}
