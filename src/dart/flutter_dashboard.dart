// Phase 634 — Dart Flutter Dashboard for SDACS real-time visualization
import 'dart:math' as math;

/// Telemetry data point from a drone.
class DroneState {
  final String id;
  final double x, y, z;
  final double batteryPct;
  final String phase;

  const DroneState({
    required this.id,
    required this.x,
    required this.y,
    required this.z,
    required this.batteryPct,
    required this.phase,
  });
}

/// Dashboard model aggregating drone states.
class DashboardModel {
  final List<DroneState> drones;

  const DashboardModel({required this.drones});

  int get activeDrones => drones.where((d) => d.phase != 'GROUNDED').length;

  double get avgBattery =>
      drones.isEmpty ? 0.0 : drones.map((d) => d.batteryPct).reduce((a, b) => a + b) / drones.length;

  double distanceBetween(DroneState a, DroneState b) {
    return math.sqrt(math.pow(a.x - b.x, 2) + math.pow(a.y - b.y, 2) + math.pow(a.z - b.z, 2));
  }
}
