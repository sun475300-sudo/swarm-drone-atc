import { useEffect, useRef, useState } from "react";
import { telemetryWsUrl } from "../api/client";
import type { TelemetryEvent } from "../api/types";

export type WsStatus = "connecting" | "open" | "closed";

interface TelemetryState {
  status: WsStatus;
  last: TelemetryEvent | null;
  messageCount: number;
}

/**
 * /ws/telemetry 구독 훅.
 * enabled=false 면 연결하지 않는다(데모 모드). 언마운트/비활성 시 정리한다.
 */
export function useTelemetry(enabled: boolean): TelemetryState {
  const [status, setStatus] = useState<WsStatus>("closed");
  const [last, setLast] = useState<TelemetryEvent | null>(null);
  const [messageCount, setMessageCount] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!enabled) {
      setStatus("closed");
      return;
    }

    let cancelled = false;
    setStatus("connecting");
    const ws = new WebSocket(telemetryWsUrl());
    socketRef.current = ws;

    ws.onopen = () => {
      if (!cancelled) setStatus("open");
    };
    ws.onmessage = (ev: MessageEvent<string>) => {
      if (cancelled) return;
      try {
        setLast(JSON.parse(ev.data) as TelemetryEvent);
        setMessageCount((n) => n + 1);
      } catch {
        // 비-JSON 프레임은 무시(서버 ping 등).
      }
    };
    ws.onclose = () => {
      if (!cancelled) setStatus("closed");
    };
    ws.onerror = () => {
      if (!cancelled) setStatus("closed");
    };

    return () => {
      cancelled = true;
      ws.close();
      socketRef.current = null;
    };
  }, [enabled]);

  return { status, last, messageCount };
}
