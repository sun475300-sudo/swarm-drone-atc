import { useAuth } from "./hooks/useAuth.js";
import { useTelemetry } from "./hooks/useTelemetry.js";
import { DroneTable } from "./components/DroneTable.jsx";
import { LoginForm } from "./components/LoginForm.jsx";
import { ScenarioPanel } from "./components/ScenarioPanel.jsx";
import { StatusBar } from "./components/StatusBar.jsx";

const styles = {
  layout: { display: "flex", flexDirection: "column", height: "100vh" },
  body: { display: "flex", flex: 1, overflow: "hidden" },
  main: { flex: 1, overflow: "auto", padding: "1rem" },
  sidebar: {
    width: 280,
    background: "#0f1624",
    borderLeft: "1px solid #2d3748",
    overflow: "auto",
  },
  section: {
    background: "#131929",
    border: "1px solid #2d3748",
    borderRadius: 8,
    marginBottom: "1rem",
    overflow: "hidden",
  },
  sectionTitle: {
    padding: "0.6rem 1rem",
    background: "#1a2234",
    borderBottom: "1px solid #2d3748",
    fontSize: 13,
    fontWeight: 600,
    color: "#90cdf4",
  },
};

export default function App() {
  const { token, login, logout, error: authError, loading: authLoading } = useAuth();
  const { drones, conflicts, connected } = useTelemetry(token);

  if (!token) {
    return <LoginForm onLogin={login} error={authError} loading={authLoading} />;
  }

  return (
    <div style={styles.layout}>
      <StatusBar
        droneCount={drones.length}
        conflictCount={conflicts.length}
        connected={connected}
        onLogout={logout}
      />
      <div style={styles.body}>
        <main style={styles.main}>
          <div style={styles.section}>
            <div style={styles.sectionTitle}>실시간 드론 현황</div>
            <DroneTable drones={drones} conflicts={conflicts} />
          </div>
        </main>
        <aside style={styles.sidebar}>
          <div style={styles.section}>
            <div style={styles.sectionTitle}>시나리오 관리</div>
            <ScenarioPanel token={token} />
          </div>
        </aside>
      </div>
    </div>
  );
}
