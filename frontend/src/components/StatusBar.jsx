const styles = {
  bar: {
    display: "flex",
    alignItems: "center",
    gap: 16,
    padding: "0.5rem 1rem",
    background: "#131929",
    borderBottom: "1px solid #2d3748",
    fontSize: 13,
  },
  title: { fontWeight: 700, color: "#90cdf4", marginRight: "auto" },
  dot: (connected) => ({
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: connected ? "#68d391" : "#fc8181",
    display: "inline-block",
    marginRight: 4,
  }),
  badge: (warn) => ({
    padding: "0.15rem 0.5rem",
    borderRadius: 4,
    background: warn ? "#742a2a" : "#1a2234",
    color: warn ? "#fc8181" : "#718096",
    fontSize: 12,
  }),
  logout: {
    padding: "0.25rem 0.6rem",
    background: "transparent",
    border: "1px solid #4a5568",
    borderRadius: 4,
    color: "#a0aec0",
    fontSize: 12,
    cursor: "pointer",
  },
};

export function StatusBar({ droneCount, conflictCount, connected, onLogout }) {
  return (
    <div style={styles.bar}>
      <span style={styles.title}>SDACS ATC</span>
      <span>
        <span style={styles.dot(connected)} />
        {connected ? "연결됨" : "연결 끊김"}
      </span>
      <span style={styles.badge(false)}>드론 {droneCount}기</span>
      <span style={styles.badge(conflictCount > 0)}>
        충돌 {conflictCount}건
      </span>
      <button style={styles.logout} onClick={onLogout}>
        로그아웃
      </button>
    </div>
  );
}
