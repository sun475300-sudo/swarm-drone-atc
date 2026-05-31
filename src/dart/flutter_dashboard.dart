// P634: Flutter Dashboard - Dart stub
// Mobile drone monitoring dashboard

import 'dart:async';
import 'dart:convert';

class DroneStatus {
  final String id;
  final List<double> position;
  final List<double> velocity;
  final double battery;
  final String status;

  const DroneStatus({
    required this.id,
    required this.position,
    required this.velocity,
    required this.battery,
    required this.status,
  });

  factory DroneStatus.fromJson(Map<String, dynamic> json) => DroneStatus(
    id: json['id'] as String,
    position: List<double>.from(json['position'] as List),
    velocity: List<double>.from(json['velocity'] as List),
    battery: (json['battery'] as num).toDouble(),
    status: json['status'] as String,
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'position': position,
    'velocity': velocity,
    'battery': battery,
    'status': status,
  };
}

class SwarmDashboardController {
  final _statusController = StreamController<List<DroneStatus>>.broadcast();
  final List<DroneStatus> _drones = [];

  Stream<List<DroneStatus>> get statusStream => _statusController.stream;

  void updateDrone(DroneStatus status) {
    final idx = _drones.indexWhere((d) => d.id == status.id);
    if (idx >= 0) {
      _drones[idx] = status;
    } else {
      _drones.add(status);
    }
    _statusController.add(List.unmodifiable(_drones));
  }

  void dispose() => _statusController.close();
}
