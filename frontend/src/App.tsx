import { useEffect, useState } from "react";
import { ApiError, fetchScenarios } from "./api/client";
import type { ScenarioCatalog } from "./api/types";
import { ScenarioList } from "./components/ScenarioList";
import { RunPanel } from "./components/RunPanel";
import { TelemetryPanel } from "./components/TelemetryPanel";

export function App() {
  const [catalog, setCatalog] = useState<ScenarioCatalog>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [token, setToken] = useState("");
  const [liveTelemetry, setLiveTelemetry] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchScenarios()
      .then((cat) => {
        if (cancelled) return;
        setCatalog(cat);
        setLoadError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const msg =
          err instanceof ApiError
            ? err.message
            : "백엔드(FastAPI)에 연결할 수 없습니다. uvicorn api.fastapi_server:app 실행 여부를 확인하세요.";
        setLoadError(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>SDACS 공역 관제 대시보드</h1>
        <input
          className="token-input"
          type="password"
          placeholder="Bearer 토큰"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
      </header>

      <main className="layout">
        <section className="panel">
          <h2>시나리오</h2>
          {loading && <p className="muted">불러오는 중…</p>}
          {loadError && <p className="error">⚠ {loadError}</p>}
          {!loading && !loadError && (
            <ScenarioList
              catalog={catalog}
              selected={selected}
              onSelect={setSelected}
            />
          )}
        </section>

        <section className="panel">
          <h2>실행</h2>
          <RunPanel scenarioId={selected} token={token} />
        </section>

        <section className="panel">
          <h2>텔레메트리</h2>
          <TelemetryPanel enabled={liveTelemetry} onToggle={setLiveTelemetry} />
        </section>
      </main>
    </div>
  );
}
