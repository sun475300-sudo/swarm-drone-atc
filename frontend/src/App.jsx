import React, { useState } from "react";
import { getToken, getRole, clearSession } from "./api.js";
import Login from "./components/Login.jsx";
import Dashboard from "./components/Dashboard.jsx";

export default function App() {
  const [authed, setAuthed] = useState(Boolean(getToken()));

  function handleLogout() {
    clearSession();
    setAuthed(false);
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>SDACS · 군집드론 공역 관제</h1>
        {authed && (
          <div className="session">
            <span className="role-badge">{getRole()}</span>
            <button onClick={handleLogout}>로그아웃</button>
          </div>
        )}
      </header>
      <main>
        {authed ? (
          <Dashboard />
        ) : (
          <Login onSuccess={() => setAuthed(true)} />
        )}
      </main>
    </div>
  );
}
