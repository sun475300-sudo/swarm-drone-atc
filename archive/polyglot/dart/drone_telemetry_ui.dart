/// SDACS 드론 텔레메트리 UI 모델 — Dart (Flutter)
/// ================================================
/// Flutter 모바일 앱용 드론 모니터링 데이터 모델
///
/// 기능:
///   - 텔레메트리 데이터 모델 (위치/배터리/상태)
///   - 실시간 스트림 관리
///   - 경보 알림 모델
///   - 지도 오버레이 데이터
///   - 상태 위젯 모델

import 'dart:math';

// ── 기본 데이터 모델 ──────────────────────────────────

class Vec3 {
  final double x, y, z;
  const Vec3(this.x, this.y, this.z);

  double distanceTo(Vec3 other) {
    final dx = x - other.x;
    final dy = y - other.y;
    final dz = z - other.z;
    return sqrt(dx * dx + dy * dy + dz * dz);
  }

  Vec3 operator +(Vec3 other) => Vec3(x + other.x, y + other.y, z + other.z);
  Vec3 operator -(Vec3 other) => Vec3(x - other.x, y - other.y, z - other.z);
  Vec3 operator *(double s) => Vec3(x * s, y * s, z * s);

  @override
  String toString() => '(${x.toStringAsFixed(1)}, ${y.toStringAsFixed(1)}, ${z.toStringAsFixed(1)})';
}

enum DroneStatus {
  idle, preflight, armed, takeoff, cruise, landing, emergency, grounded, rtl
}

enum AlertSeverity { info, warning, critical, emergency }

class DroneTelemetry {
  final String droneId;
  final Vec3 position;
  final Vec3 velocity;
  final double heading;
  final double batteryPct;
  final double speedMs;
  final DroneStatus status;
  final DateTime timestamp;
  final int gpsSatellites;
  final double signalStrength;

  const DroneTelemetry({
    required this.droneId,
    required this.position,
    this.velocity = const Vec3(0, 0, 0),
    this.heading = 0.0,
    this.batteryPct = 100.0,
    this.speedMs = 0.0,
    this.status = DroneStatus.idle,
    required this.timestamp,
    this.gpsSatellites = 12,
    this.signalStrength = 100.0,
  });

  factory DroneTelemetry.fromJson(Map<String, dynamic> json) {
    return DroneTelemetry(
      droneId: json['drone_id'] as String,
      position: Vec3(
        (json['position'][0] as num).toDouble(),
        (json['position'][1] as num).toDouble(),
        (json['position'][2] as num).toDouble(),
      ),
      velocity: Vec3(
        (json['velocity']?[0] as num?)?.toDouble() ?? 0,
        (json['velocity']?[1] as num?)?.toDouble() ?? 0,
        (json['velocity']?[2] as num?)?.toDouble() ?? 0,
      ),
      heading: (json['heading'] as num?)?.toDouble() ?? 0,
      batteryPct: (json['battery_pct'] as num?)?.toDouble() ?? 100,
      speedMs: (json['speed_ms'] as num?)?.toDouble() ?? 0,
      status: DroneStatus.values.firstWhere(
        (s) => s.name == (json['status'] as String?)?.toLowerCase(),
        orElse: () => DroneStatus.idle,
      ),
      timestamp: DateTime.now(),
      gpsSatellites: (json['gps_satellites'] as int?) ?? 12,
      signalStrength: (json['signal_strength'] as num?)?.toDouble() ?? 100,
    );
  }

  Map<String, dynamic> toJson() => {
    'drone_id': droneId,
    'position': [position.x, position.y, position.z],
    'velocity': [velocity.x, velocity.y, velocity.z],
    'heading': heading,
    'battery_pct': batteryPct,
    'speed_ms': speedMs,
    'status': status.name,
    'gps_satellites': gpsSatellites,
    'signal_strength': signalStrength,
  };

  bool get isCritical => batteryPct < 15 || status == DroneStatus.emergency;
  bool get isLowBattery => batteryPct < 30;
  String get batteryIcon => batteryPct > 75 ? 'full' : batteryPct > 50 ? 'three_quarters' : batteryPct > 25 ? 'half' : 'low';
}

// ── 경보 모델 ────────────────────────────────────────

class AlertModel {
  final String alertId;
  final String title;
  final String message;
  final AlertSeverity severity;
  final DateTime timestamp;
  final String? droneId;
  final Vec3? location;
  bool acknowledged;

  AlertModel({
    required this.alertId,
    required this.title,
    required this.message,
    required this.severity,
    required this.timestamp,
    this.droneId,
    this.location,
    this.acknowledged = false,
  });

  String get severityColor {
    switch (severity) {
      case AlertSeverity.info: return '#2196F3';
      case AlertSeverity.warning: return '#FF9800';
      case AlertSeverity.critical: return '#F44336';
      case AlertSeverity.emergency: return '#D32F2F';
    }
  }
}

// ── KPI 대시보드 모델 ───────────────────────────────────

class KPIDashboard {
  final int activeDrones;
  final int totalConflicts;
  final int resolvedConflicts;
  final double collisionRate;
  final double avgBattery;
  final double throughput;
  final double p50Latency;
  final double p99Latency;
  final String overallHealth;

  const KPIDashboard({
    this.activeDrones = 0,
    this.totalConflicts = 0,
    this.resolvedConflicts = 0,
    this.collisionRate = 0.0,
    this.avgBattery = 100.0,
    this.throughput = 0.0,
    this.p50Latency = 0.0,
    this.p99Latency = 0.0,
    this.overallHealth = 'OK',
  });

  double get resolutionRate =>
    totalConflicts > 0 ? resolvedConflicts / totalConflicts : 1.0;

  String get healthColor {
    switch (overallHealth) {
      case 'OK': return '#4CAF50';
      case 'WARNING': return '#FF9800';
      case 'CRITICAL': return '#F44336';
      default: return '#9E9E9E';
    }
  }

  factory KPIDashboard.fromJson(Map<String, dynamic> json) => KPIDashboard(
    activeDrones: json['active_drones'] ?? 0,
    totalConflicts: json['total_conflicts'] ?? 0,
    resolvedConflicts: json['resolved_conflicts'] ?? 0,
    collisionRate: (json['collision_rate'] as num?)?.toDouble() ?? 0,
    avgBattery: (json['avg_battery'] as num?)?.toDouble() ?? 100,
    throughput: (json['throughput'] as num?)?.toDouble() ?? 0,
    p50Latency: (json['p50_latency'] as num?)?.toDouble() ?? 0,
    p99Latency: (json['p99_latency'] as num?)?.toDouble() ?? 0,
    overallHealth: json['overall_health'] ?? 'OK',
  );
}

// ── 지도 오버레이 모델 ──────────────────────────────────

class MapOverlay {
  final String id;
  final String type; // 'nfz', 'corridor', 'heatmap', 'trail'
  final List<Vec3> points;
  final String color;
  final double opacity;
  final bool visible;

  const MapOverlay({
    required this.id,
    required this.type,
    required this.points,
    this.color = '#FF0000',
    this.opacity = 0.5,
    this.visible = true,
  });
}

// ── 텔레메트리 스트림 관리자 ────────────────────────────

class TelemetryStreamManager {
  final Map<String, DroneTelemetry> _latestTelemetry = {};
  final List<AlertModel> _alerts = [];
  KPIDashboard _kpi = const KPIDashboard();
  final List<void Function(DroneTelemetry)> _listeners = [];

  void onTelemetry(DroneTelemetry t) {
    _latestTelemetry[t.droneId] = t;

    // 자동 경보 생성
    if (t.isCritical) {
      addAlert(AlertModel(
        alertId: 'auto_${t.droneId}_${DateTime.now().millisecondsSinceEpoch}',
        title: '${t.droneId} 비상 상태',
        message: '배터리: ${t.batteryPct}%, 상태: ${t.status.name}',
        severity: AlertSeverity.emergency,
        timestamp: DateTime.now(),
        droneId: t.droneId,
        location: t.position,
      ));
    }

    for (final listener in _listeners) {
      listener(t);
    }
  }

  void addAlert(AlertModel alert) {
    _alerts.insert(0, alert);
    if (_alerts.length > 100) _alerts.removeLast();
  }

  void updateKPI(KPIDashboard kpi) { _kpi = kpi; }
  void addListener(void Function(DroneTelemetry) fn) => _listeners.add(fn);

  List<DroneTelemetry> get allDrones => _latestTelemetry.values.toList();
  List<AlertModel> get recentAlerts => _alerts.take(20).toList();
  KPIDashboard get kpi => _kpi;
  int get droneCount => _latestTelemetry.length;

  Map<String, dynamic> summary() => {
    'drones': droneCount,
    'alerts': _alerts.length,
    'kpi_health': _kpi.overallHealth,
  };
}
