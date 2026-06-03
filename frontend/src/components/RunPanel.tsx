import { useState } from "react";
import { ApiError, fetchRun, startRun } from "../api/client";
import type { RunRecordData, RunScenarioBody } from "../api/types";

interface Props {
  scenarioId: string | null;
  token: string;
}

const METHODS: RunScenarioBody["method"][] = ["hybrid", "orca", "apf", "cbs"];
const POLL_INTERVAL_MS = 1000;
const MAX_POLLS = 120;

export function RunPanel({ scenarioId, token }: Props) {
  const [method, setMethod] = useState<RunScenarioBody["method"]>("hybrid");
  const [seed, setSeed] = useState(42);
  const [durationS, setDurationS] = useState(60);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<RunRecordData | null>(null);

  async function pollUntilDone(runId: string): Promise<void> {
    for (let i = 0; i < MAX_POLLS; i += 1) {
      const record = await fetchRun(runId);
      setRun(record);
      if (record.status === "completed" || record.status === "failed") return;
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    }
  }

  async function onRun() {
    if (!scenarioId) return;
    setBusy(true);
    setError(null);
    setRun(null);
    try {
      const started = await startRun(
        scenarioId,
        { seed, method, duration_s: durationS },
        token,
      );
      await pollUntilDone(started.run_id);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `${err.message} (HTTP ${err.status})`
          : err instanceof Error
            ? err.message
            : String(err);
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  const canRun = Boolean(scenarioId) && token.length > 0 && !busy;

  return (
    <div className="run-panel">
      <div className="field-row">
        <label>
          방식
          <select
            value={method}
            onChange={(e) =>
              setMethod(e.target.value as RunScenarioBody["method"])
            }
          >
            {METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label>
          시드
          <input
            type="number"
            min={0}
            value={seed}
            onChange={(e) => setSeed(Number(e.target.value))}
          />
        </label>
        <label>
          시간(s)
          <input
            type="number"
            min={1}
            max={3600}
            value={durationS}
            onChange={(e) => setDurationS(Number(e.target.value))}
          />
        </label>
      </div>

      <button type="button" disabled={!canRun} onClick={onRun}>
        {busy ? "실행 중…" : "시나리오 실행"}
      </button>
      {!token && <p className="muted">실행하려면 상단에 Bearer 토큰을 입력하세요.</p>}
      {!scenarioId && <p className="muted">먼저 시나리오를 선택하세요.</p>}

      {error && <p className="error">⚠ {error}</p>}

      {run && (
        <div className="run-result">
          <p>
            <strong>{run.run_id.slice(0, 8)}</strong> — 상태:{" "}
            <span className={`status status-${run.status}`}>{run.status}</span>
          </p>
          {run.status === "completed" && (
            <pre className="metrics">
              {JSON.stringify(run.metrics, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
