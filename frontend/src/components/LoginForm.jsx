import { useState } from "react";

const styles = {
  overlay: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "100vh",
    background: "#0a0e1a",
  },
  card: {
    background: "#131929",
    border: "1px solid #2d3748",
    borderRadius: 12,
    padding: "2.5rem",
    width: 360,
    boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
  },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 4, color: "#90cdf4" },
  subtitle: { fontSize: 13, color: "#718096", marginBottom: 24 },
  label: { display: "block", fontSize: 12, color: "#a0aec0", marginBottom: 6 },
  input: {
    width: "100%",
    padding: "0.6rem 0.8rem",
    background: "#0a0e1a",
    border: "1px solid #2d3748",
    borderRadius: 6,
    color: "#e2e8f0",
    fontSize: 14,
    marginBottom: 16,
    outline: "none",
  },
  button: {
    width: "100%",
    padding: "0.7rem",
    background: "#3182ce",
    border: "none",
    borderRadius: 6,
    color: "#fff",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  },
  error: {
    background: "#742a2a",
    border: "1px solid #e53e3e",
    borderRadius: 6,
    padding: "0.6rem 0.8rem",
    fontSize: 13,
    color: "#feb2b2",
    marginBottom: 16,
  },
};

export function LoginForm({ onLogin, error, loading }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    onLogin(username, password);
  }

  return (
    <div style={styles.overlay}>
      <form style={styles.card} onSubmit={handleSubmit}>
        <div style={styles.title}>SDACS</div>
        <div style={styles.subtitle}>군집드론 공역통제 자동화 시스템</div>
        {error && <div style={styles.error}>{error}</div>}
        <label style={styles.label}>사용자명</label>
        <input
          style={styles.input}
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          required
        />
        <label style={styles.label}>비밀번호</label>
        <input
          style={styles.input}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
        <button style={styles.button} type="submit" disabled={loading}>
          {loading ? "로그인 중…" : "로그인"}
        </button>
      </form>
    </div>
  );
}
