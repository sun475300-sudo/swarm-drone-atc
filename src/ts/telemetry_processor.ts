/**
 * Phase 292: TypeScript Telemetry Stream Processor
 * 실시간 텔레메트리 수집, 윈도우 집계, 이상치 탐지.
 */

export enum TelemetryField {
  ALTITUDE = 'altitude',
  SPEED = 'speed',
  BATTERY = 'battery',
  TEMPERATURE = 'temperature',
  VIBRATION = 'vibration',
  GPS_ACCURACY = 'gps_accuracy',
  SIGNAL_STRENGTH = 'signal_strength',
  MOTOR_RPM = 'motor_rpm',
}

export interface TelemetryPoint {
  droneId: string;
  timestamp: number;
  field: TelemetryField;
  value: number;
}

export interface AnomalyAlert {
  droneId: string;
  field: TelemetryField;
  value: number;
  expectedRange: [number, number];
  severity: 'warning' | 'critical';
  timestamp: number;
}

interface StreamWindow {
  values: number[];
  maxSize: number;
}

const THRESHOLDS: Record<TelemetryField, [number, number]> = {
  [TelemetryField.ALTITUDE]: [0, 500],
  [TelemetryField.SPEED]: [0, 30],
  [TelemetryField.BATTERY]: [10, 100],
  [TelemetryField.TEMPERATURE]: [-20, 60],
  [TelemetryField.VIBRATION]: [0, 5],
  [TelemetryField.GPS_ACCURACY]: [0, 10],
  [TelemetryField.SIGNAL_STRENGTH]: [-100, 0],
  [TelemetryField.MOTOR_RPM]: [0, 12000],
};

function mean(arr: number[]): number {
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function stddev(arr: number[]): number {
  if (arr.length < 2) return 0;
  const m = mean(arr);
  return Math.sqrt(arr.reduce((sum, v) => sum + (v - m) ** 2, 0) / (arr.length - 1));
}

export class TelemetryStreamProcessor {
  private windows: Map<string, Map<TelemetryField, StreamWindow>> = new Map();
  private alerts: AnomalyAlert[] = [];
  private totalPoints = 0;
  private zThreshold: number;
  private windowSize: number;

  constructor(windowSize = 100, zThreshold = 3.0) {
    this.windowSize = windowSize;
    this.zThreshold = zThreshold;
  }

  ingest(point: TelemetryPoint): AnomalyAlert | null {
    this.totalPoints++;
    if (!this.windows.has(point.droneId)) {
      this.windows.set(point.droneId, new Map());
    }
    const droneWindows = this.windows.get(point.droneId)!;
    if (!droneWindows.has(point.field)) {
      droneWindows.set(point.field, { values: [], maxSize: this.windowSize });
    }
    const window = droneWindows.get(point.field)!;
    window.values.push(point.value);
    if (window.values.length > window.maxSize) {
      window.values.shift();
    }

    // Threshold check
    const [lo, hi] = THRESHOLDS[point.field] ?? [-Infinity, Infinity];
    if (point.value < lo || point.value > hi) {
      const severity = point.value < lo * 0.5 || point.value > hi * 1.5 ? 'critical' : 'warning';
      const alert: AnomalyAlert = {
        droneId: point.droneId,
        field: point.field,
        value: point.value,
        expectedRange: [lo, hi],
        severity,
        timestamp: point.timestamp,
      };
      this.alerts.push(alert);
      return alert;
    }

    // Z-score check
    if (window.values.length > 10) {
      const m = mean(window.values);
      const s = stddev(window.values);
      const z = Math.abs(point.value - m) / Math.max(s, 1e-6);
      if (z > this.zThreshold) {
        const alert: AnomalyAlert = {
          droneId: point.droneId,
          field: point.field,
          value: point.value,
          expectedRange: [m - 2 * s, m + 2 * s],
          severity: 'warning',
          timestamp: point.timestamp,
        };
        this.alerts.push(alert);
        return alert;
      }
    }
    return null;
  }

  getWindowStats(droneId: string, field: TelemetryField) {
    const w = this.windows.get(droneId)?.get(field);
    if (!w || w.values.length === 0) return null;
    return {
      field,
      count: w.values.length,
      mean: mean(w.values).toFixed(3),
      std: stddev(w.values).toFixed(3),
      min: Math.min(...w.values).toFixed(3),
      max: Math.max(...w.values).toFixed(3),
      latest: w.values[w.values.length - 1].toFixed(3),
    };
  }

  getAlerts(droneId?: string): AnomalyAlert[] {
    return droneId ? this.alerts.filter(a => a.droneId === droneId) : [...this.alerts];
  }

  summary() {
    const severityCounts: Record<string, number> = {};
    for (const a of this.alerts) {
      severityCounts[a.severity] = (severityCounts[a.severity] || 0) + 1;
    }
    return {
      trackedDrones: this.windows.size,
      totalPointsIngested: this.totalPoints,
      totalAlerts: this.alerts.length,
      severityCounts,
    };
  }
}
