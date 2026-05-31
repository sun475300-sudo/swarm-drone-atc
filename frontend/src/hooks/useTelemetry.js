import { useCallback, useEffect, useRef, useState } from "react";
import { connectTelemetry } from "../api/client.js";

export function useTelemetry(token) {
  const [drones, setDrones] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  const reconnect = useCallback(() => {
    if (wsRef.current) wsRef.current.close();

    const ws = connectTelemetry(token, (frame) => {
      if (frame.drones !== undefined) setDrones(frame.drones);
      if (frame.conflicts !== undefined) setConflicts(frame.conflicts);
    });

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    wsRef.current = ws;
  }, [token]);

  useEffect(() => {
    if (!token) return;
    reconnect();
    return () => wsRef.current?.close();
  }, [token, reconnect]);

  return { drones, conflicts, connected, reconnect };
}
