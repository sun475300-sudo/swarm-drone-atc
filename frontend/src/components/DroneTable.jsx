const styles = {
  table: { width: "100%", borderCollapse: "collapse", fontSize: 13 },
  th: {
    padding: "0.5rem 0.75rem",
    background: "#1a2234",
    color: "#90cdf4",
    fontWeight: 600,
    textAlign: "left",
    borderBottom: "1px solid #2d3748",
  },
  td: {
    padding: "0.4rem 0.75rem",
    borderBottom: "1px solid #1a2234",
    color: "#cbd5e0",
  },
  conflict: { color: "#fc8181" },
};

export function DroneTable({ drones, conflicts }) {
  const conflictIds = new Set(conflicts.flatMap((c) => [c.drone_a, c.drone_b]));

  return (
    <table style={styles.table}>
      <thead>
        <tr>
          <th style={styles.th}>ID</th>
          <th style={styles.th}>위도</th>
          <th style={styles.th}>경도</th>
          <th style={styles.th}>고도(m)</th>
          <th style={styles.th}>상태</th>
        </tr>
      </thead>
      <tbody>
        {drones.map((d) => {
          const hasConflict = conflictIds.has(d.id);
          return (
            <tr key={d.id}>
              <td style={{ ...styles.td, ...(hasConflict ? styles.conflict : {}) }}>
                {d.id}
              </td>
              <td style={styles.td}>{d.lat?.toFixed(5) ?? "—"}</td>
              <td style={styles.td}>{d.lon?.toFixed(5) ?? "—"}</td>
              <td style={styles.td}>{d.alt?.toFixed(1) ?? "—"}</td>
              <td style={{ ...styles.td, ...(hasConflict ? styles.conflict : {}) }}>
                {hasConflict ? "⚠ 충돌위험" : "정상"}
              </td>
            </tr>
          );
        })}
        {drones.length === 0 && (
          <tr>
            <td colSpan={5} style={{ ...styles.td, textAlign: "center", color: "#4a5568" }}>
              드론 데이터 없음
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
