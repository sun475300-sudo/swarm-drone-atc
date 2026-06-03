import { useEffect, useState } from "react";
import { telemetryWsUrl } from "../api/client";
import type { TelemetryEvent } from "../api/types";

export type WsStatus = "connecting" | "open" | "closed";

interface TelemetryState {
  status: WsStatus;
  last: TelemetryEvent | null;
  messageCount: number;
}

const BASE_RETRY_MS = 1000;
const MAX_RETRY_MS = 30000;

/**
 * /ws/telemetry 구독 훅.
 * enabled=false 면 연결하지 않는다(데모 모드).
 * 연결이 끊기면 지수 백오프(1s→30s)로 자동 재연결한다.
 * 언마운트/비활성 시 소켓·타이머를 정리한다.
 */
export function useTelemetry(enabled: boolean): TelemetryState {
  const [status, setStatus] = useState<WsStatus>("closed");
  const [last, setLast] = useState<TelemetryEvent | null>(null);
  const [messageCount, setMessageCount] = useState(0);

  useEffect(() => {
    if (!enabled) {
      setStatus("closed");
      return;
    }

    let cancelled = false;
    let ws: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;

    function connect() {
      if (cancelled) return;
      setStatus("connecting");
      ws = new WebSocket(telemetryWsUrl());

      ws.onopen = () => {
        if (cancelled) return;
        attempt = 0; // 성공 시 백오프 리셋
        setStatus("open");
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
      const scheduleReconnect = () => {
        if (cancelled) return;
        setStatus("closed");
        const delay = Math.min(BASE_RETRY_MS * 2 ** attempt, MAX_RETRY_MS);
        attempt += 1;
        retryTimer = setTimeout(connect, delay);
      };
      ws.onclose = scheduleReconnect;
      ws.onerror = () => ws?.close();
    }

    connect();

    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      ws?.close();
    };
  }, [enabled]);

  return { status, last, messageCount };
}
