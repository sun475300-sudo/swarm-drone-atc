import { useEffect, useState } from "react";
import { fetchRun, fetchScenarios, runScenario } from "../api/client.js";

const styles = {
  panel: { padding: "1rem" },
  heading: { fontSize: 14, fontWeight: 600, color: "#90cdf4", marginBottom: 12 },
  row: { display: "flex", alignItems: "center", gap: 8, marginBottom: 8 },
  name: { flex: 1, fontSize: 13, color: "#cbd5e0" },
  button: {
    padding: "0.3rem 0.7rem",
    background: "#2b6cb0",
    border: "none",
    borderRadius: 5,
    color: "#fff",
    fontSize: 12,
    cursor: "pointer",
  },
  status: { fontSize: 12, color: "#68d391" },
  error: { fontSize: 12, color: "#fc8181" },
};

export function ScenarioPanel({ token }) {
  const [scenarios, setScenarios] = useState([]);
  const [runs, setRuns] = useState({});
  const [busy, setBusy] = useState({});

  useEffect(() => {
    if (!token) return;
    fetchScenarios(token)
      .then(setScenarios)
      .catch(() => {});
  }, [token]);

  async function handleRun(scenarioId) {
    setBusy((b) => ({ ...b, [scenarioId]: true }));
    try {
      const { run_id } = await runScenario(token, scenarioId);
      setRuns((r) => ({ ...r, [scenarioId]: { run_id, status: "queued" } }));

      const poll = setInterval(async () => {
        try {
          const run = await fetchRun(token, run_id);
          setRuns((r) => ({ ...r, [scenarioId]: run }));
          if (run.status === "completed" || run.status === "failed") {
            clearInterval(poll);
            setBusy((b) => ({ ...b, [scenarioId]: false }));
          }
        } catch {
          clearInterval(poll);
          setBusy((b) => ({ ...b, [scenarioId]: false }));
        }
      }, 2000);
    } catch {
      setBusy((b) => ({ ...b, [scenarioId]: false }));
    }
  }

  return (
    <div style={styles.panel}>
      <div style={styles.heading}>시나리오</div>
      {scenarios.map((s) => {
        const run = runs[s.id];
        return (
          <div key={s.id} style={styles.row}>
            <span style={styles.name}>{s.name ?? s.id}</span>
            {run && (
              <span style={run.status === "failed" ? styles.error : styles.status}>
                {run.status}
              </span>
            )}
            <button
              style={styles.button}
              disabled={busy[s.id]}
              onClick={() => handleRun(s.id)}
            >
              {busy[s.id] ? "실행 중…" : "실행"}
            </button>
          </div>
        );
      })}
      {scenarios.length === 0 && (
        <div style={{ fontSize: 13, color: "#4a5568" }}>시나리오 없음</div>
      )}
    </div>
  );
}
