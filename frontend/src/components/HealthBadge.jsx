import React, { useEffect, useState } from "react";
import { getHealth } from "../api.js";

export default function HealthBadge() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    getHealth()
      .then((h) => active && setHealth(h))
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, []);

  if (error) return <div className="health err">백엔드 연결 실패: {error}</div>;
  if (!health) return <div className="health">상태 확인 중…</div>;
  return (
    <div className="health ok">
      <strong>API {health.version}</strong> · {health.status}
      {health.gpu?.backend && <span> · {health.gpu.backend}</span>}
    </div>
  );
}
