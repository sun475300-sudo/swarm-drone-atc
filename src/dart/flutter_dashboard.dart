// SDACS Flutter Dashboard — Dart
// 드론 군집 실시간 모니터링 대시보드

import 'dart:math' as math;
import 'dart:async';

class DroneStatus {
  final String id;
  final double x;
  final double y;
  final double altitude;
  final double battery;
  final String state;
  final DateTime lastUpdate;

  const DroneStatus({
    required this.id,
    required this.x,
    required this.y,
    required this.altitude,
    required this.battery,
    required this.state,
    required this.lastUpdate,
  });

  DroneStatus copyWith({
    double? x, double? y, double? altitude, double? battery, String? state,
  }) => DroneStatus(
    id: id,
    x: x ?? this.x,
    y: y ?? this.y,
    altitude: altitude ?? this.altitude,
    battery: battery ?? this.battery,
    state: state ?? this.state,
    lastUpdate: DateTime.now(),
  );

  bool get isLowBattery => battery < 20.0;
  bool get isActive => state == 'FLYING' || state == 'HOVERING';
}

class FleetDashboard {
  final Map<String, DroneStatus> _fleet = {};
  final StreamController<List<DroneStatus>> _controller =
      StreamController.broadcast();

  Stream<List<DroneStatus>> get stream => _controller.stream;

  void updateDrone(DroneStatus status) {
    _fleet[status.id] = status;
    _controller.add(activeDrones);
  }

  List<DroneStatus> get activeDrones =>
      _fleet.values.where((d) => d.isActive).toList();

  List<DroneStatus> get lowBatteryDrones =>
      _fleet.values.where((d) => d.isLowBattery).toList();

  int get totalCount => _fleet.length;

  double get averageAltitude {
    if (_fleet.isEmpty) return 0.0;
    return _fleet.values.map((d) => d.altitude).reduce((a, b) => a + b) /
        _fleet.length;
  }

  double get averageBattery {
    if (_fleet.isEmpty) return 0.0;
    return _fleet.values.map((d) => d.battery).reduce((a, b) => a + b) /
        _fleet.length;
  }

  List<String> detectConflicts({double threshold = 50.0}) {
    final alerts = <String>[];
    final drones = _fleet.values.toList();
    for (var i = 0; i < drones.length; i++) {
      for (var j = i + 1; j < drones.length; j++) {
        final a = drones[i];
        final b = drones[j];
        final dist = math.sqrt(
          math.pow(a.x - b.x, 2) + math.pow(a.y - b.y, 2),
        );
        if (dist < threshold) {
          alerts.add('CONFLICT: ${a.id} <-> ${b.id} dist=${dist.toStringAsFixed(1)}m');
        }
      }
    }
    return alerts;
  }

  Map<String, dynamic> summary() => {
    'total': totalCount,
    'active': activeDrones.length,
    'low_battery': lowBatteryDrones.length,
    'avg_altitude': averageAltitude,
    'avg_battery': averageBattery,
  };

  void dispose() => _controller.close();
}

class TelemetryChart {
  final int maxPoints;
  final List<MapEntry<DateTime, double>> _series = [];

  TelemetryChart({this.maxPoints = 200});

  void addPoint(DateTime time, double value) {
    _series.add(MapEntry(time, value));
    if (_series.length > maxPoints) _series.removeAt(0);
  }

  List<double> get values => _series.map((e) => e.value).toList();

  double get latest => _series.isEmpty ? 0.0 : _series.last.value;

  double get trend {
    if (_series.length < 2) return 0.0;
    final recent = _series.length > 10 ? _series.sublist(_series.length - 10) : _series;
    final first = recent.first.value;
    final last = recent.last.value;
    return last - first;
  }
}
