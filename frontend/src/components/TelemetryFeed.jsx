import React, { useEffect, useRef, useState } from "react";
import { connectTelemetry } from "../api.js";

const MAX_EVENTS = 30;

export default function TelemetryFeed() {
  const [status, setStatus] = useState("connecting");
  const [events, setEvents] = useState([]);
  const closeRef = useRef(null);

  useEffect(() => {
    closeRef.current = connectTelemetry({
      onStatus: setStatus,
      onMessage: (msg) =>
        setEvents((prev) => [msg, ...prev].slice(0, MAX_EVENTS)),
    });
    return () => closeRef.current?.();
  }, []);

  return (
    <section className="card">
      <h2>
        실시간 텔레메트리 <span className={`dot ${status}`} />
      </h2>
      <p className="hint">WebSocket: {status}</p>
      <ul className="telemetry">
        {events.map((e, i) => (
          <li key={e.t ?? i}>{e.type || "event"} · {JSON.stringify(e).slice(0, 80)}</li>
        ))}
        {events.length === 0 && <li className="hint">수신 대기 중…</li>}
      </ul>
    </section>
  );
}
