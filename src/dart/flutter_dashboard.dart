// Phase 634 — Dart Flutter Dashboard for SDACS ATC
import 'dart:async';

class DroneState {
  final String id;
  final double x, y, z;
  final double batteryPct;
  const DroneState({required this.id, required this.x, required this.y, required this.z, required this.batteryPct});
}

class AirspaceDashboard {
  final _droneStream = StreamController<List<DroneState>>.broadcast();
  Stream<List<DroneState>> get droneUpdates => _droneStream.stream;
  List<DroneState> _drones = [];

  void updateDrone(DroneState state) {
    _drones = [
      ..._drones.where((d) => d.id != state.id),
      state,
    ];
    _droneStream.add(_drones);
  }

  void dispose() => _droneStream.close();
}
