// SDACS Phase 611 — TypeScript WebSocket dashboard API adapter
export interface DroneState { id: string; lat: number; lon: number; alt: number; battery: number; }
export function connectTelemetry(url: string, onUpdate: (d: DroneState[]) => void): WebSocket {
  const ws = new WebSocket(url);
  ws.onmessage = (e) => onUpdate(JSON.parse(e.data).drones ?? []);
  return ws;
}
