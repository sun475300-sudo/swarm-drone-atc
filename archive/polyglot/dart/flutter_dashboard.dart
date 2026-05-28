// Phase 634: Flutter Dashboard — Dart Cross-platform Monitor
// 크로스플랫폼 모니터링 UI 위젯

class DroneData {
  final String droneId;
  final double x, y, z;
  final double battery;
  final String status;
  final DateTime timestamp;

  DroneData({
    required this.droneId,
    required this.x,
    required this.y,
    required this.z,
    required this.battery,
    required this.status,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  bool get isLowBattery => battery < 0.2;
  bool get isActive => status != 'idle';
  double get altitude => z;

  Map<String, dynamic> toJson() => {
    'drone_id': droneId,
    'position': {'x': x, 'y': y, 'z': z},
    'battery': battery,
    'status': status,
    'timestamp': timestamp.toIso8601String(),
  };

  factory DroneData.fromJson(Map<String, dynamic> json) {
    final pos = json['position'] as Map<String, dynamic>;
    return DroneData(
      droneId: json['drone_id'] as String,
      x: (pos['x'] as num).toDouble(),
      y: (pos['y'] as num).toDouble(),
      z: (pos['z'] as num).toDouble(),
      battery: (json['battery'] as num).toDouble(),
      status: json['status'] as String,
    );
  }
}

class FleetSummary {
  final int totalDrones;
  final int activeDrones;
  final int lowBatteryCount;
  final int alertCount;
  final double avgBattery;

  FleetSummary({
    required this.totalDrones,
    required this.activeDrones,
    required this.lowBatteryCount,
    required this.alertCount,
    required this.avgBattery,
  });

  factory FleetSummary.fromDrones(List<DroneData> drones) {
    final active = drones.where((d) => d.isActive).length;
    final lowBat = drones.where((d) => d.isLowBattery).length;
    final avgBat = drones.isEmpty
        ? 0.0
        : drones.map((d) => d.battery).reduce((a, b) => a + b) / drones.length;
    return FleetSummary(
      totalDrones: drones.length,
      activeDrones: active,
      lowBatteryCount: lowBat,
      alertCount: lowBat,
      avgBattery: avgBat,
    );
  }
}

class DashboardState {
  final List<DroneData> _drones = [];
  final List<String> _alerts = [];
  bool isConnected = false;

  void updateDrone(DroneData data) {
    _drones.removeWhere((d) => d.droneId == data.droneId);
    _drones.add(data);
    if (data.isLowBattery) {
      _alerts.add('Low battery: ${data.droneId} (${(data.battery * 100).toInt()}%)');
    }
  }

  FleetSummary get summary => FleetSummary.fromDrones(_drones);
  List<DroneData> get drones => List.unmodifiable(_drones);
  List<String> get alerts => List.unmodifiable(_alerts);

  List<DroneData> getNearby(double cx, double cy, double radius) {
    return _drones.where((d) {
      final dx = d.x - cx;
      final dy = d.y - cy;
      return dx * dx + dy * dy <= radius * radius;
    }).toList();
  }
}
