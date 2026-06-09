import React, { useEffect, useState } from "react";
import { listScenarios, runScenario, getRun } from "../api.js";

const POLL_INTERVAL_MS = 1500;
const TERMINAL = new Set(["completed", "failed"]);

export default function ScenarioList() {
  const [scenarios, setScenarios] = useState([]);
  const [error, setError] = useState(null);
  const [activeRun, setActiveRun] = useState(null); // {run_id, status, scenario_id, metrics?}

  useEffect(() => {
    let active = true;
    listScenarios()
      .then((s) => active && setScenarios(s))
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, []);

  // 실행 중인 run 을 종료 상태까지 폴링한다.
  // run_id 에만 의존 → 매 폴링 결과(setActiveRun)마다 인터벌이 재생성되지 않는다.
  const runId = activeRun?.run_id;
  const isTerminal = activeRun ? TERMINAL.has(activeRun.status) : true;
  useEffect(() => {
    if (!runId || isTerminal) return;
    let cancelled = false;
    const timer = setInterval(async () => {
      try {
        const updated = await getRun(runId);
        if (cancelled) return;
        setActiveRun(updated);
        if (TERMINAL.has(updated.status)) clearInterval(timer);
      } catch (e) {
        if (!cancelled) setError(e.message);
        clearInterval(timer);
      }
    }, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [runId, isTerminal]);

  async function handleRun(scenarioId) {
    setError(null);
    try {
      const queued = await runScenario(scenarioId);
      setActiveRun({ ...queued, scenario_id: scenarioId });
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <section className="card">
      <h2>시나리오</h2>
      {error && <p className="error">{error}</p>}
      <ul className="scenario-list">
        {scenarios.map((s) => (
          <li key={s.id}>
            <span>{s.title || s.name || s.id}</span>
            <button onClick={() => handleRun(s.id)}>실행</button>
          </li>
        ))}
        {scenarios.length === 0 && !error && <li>불러오는 중…</li>}
      </ul>
      {activeRun && (
        <div className="run-status">
          <p>
            <code>{activeRun.scenario_id}</code> · {activeRun.status}
          </p>
          {TERMINAL.has(activeRun.status) && activeRun.metrics && (
            <pre>{JSON.stringify(activeRun.metrics, null, 2)}</pre>
          )}
        </div>
      )}
    </section>
  );
}
