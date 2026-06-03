import { useTelemetry } from "../hooks/useTelemetry";

interface Props {
  enabled: boolean;
  onToggle: (on: boolean) => void;
}

const STATUS_LABEL: Record<string, string> = {
  connecting: "연결 중…",
  open: "연결됨",
  closed: "끊김",
};

export function TelemetryPanel({ enabled, onToggle }: Props) {
  const { status, last, messageCount } = useTelemetry(enabled);

  const droneCount = Array.isArray(last?.drones) ? last!.drones.length : 0;
  const conflictCount = Array.isArray(last?.conflicts)
    ? last!.conflicts.length
    : 0;

  return (
    <div className="telemetry-panel">
      <label className="toggle">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onToggle(e.target.checked)}
        />
        실시간 텔레메트리 (WS)
      </label>

      {enabled && (
        <div className="telemetry-stats">
          <span className={`ws-status ws-${status}`}>
            {STATUS_LABEL[status] ?? status}
          </span>
          <span>수신 {messageCount}건</span>
          <span>드론 {droneCount}</span>
          <span>충돌 {conflictCount}</span>
        </div>
      )}
    </div>
  );
}
