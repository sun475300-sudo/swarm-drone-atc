import React, { useEffect, useState } from "react";
import { getSnapshot } from "../api.js";

const REFRESH_MS = 2000;

export default function SnapshotPanel() {
  const [snap, setSnap] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    async function poll() {
      try {
        const data = await getSnapshot();
        if (active) setSnap(data);
      } catch (e) {
        if (active) setError(e.message);
      }
    }
    poll();
    const timer = setInterval(poll, REFRESH_MS);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const drones = snap?.drones || [];
  const conflicts = snap?.conflicts || [];

  return (
    <section className="card">
      <h2>공역 스냅샷</h2>
      {error && <p className="error">{error}</p>}
      <div className="metrics">
        <div>
          <span className="num">{drones.length}</span>
          <span className="lbl">드론</span>
        </div>
        <div>
          <span className="num warn">{conflicts.length}</span>
          <span className="lbl">충돌 경고</span>
        </div>
      </div>
    </section>
  );
}
