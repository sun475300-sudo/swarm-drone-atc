// Phase 634: Flutter Dashboard — Dart
// SDACS cross-platform drone fleet dashboard built with Flutter

import 'dart:async';
import 'dart:math';

class DroneState {
  final String id;
  final double lat, lon, alt, battery, speed;
  final String mode;
  const DroneState({required this.id, required this.lat, required this.lon,
    required this.alt, required this.battery, required this.speed, required this.mode});
}

class FleetDashboardModel {
  final _stateCtrl = StreamController<List<DroneState>>.broadcast();
  final Map<String, DroneState> _drones = {};

  Stream<List<DroneState>> get droneStream => _stateCtrl.stream;

  void update(DroneState state) {
    _drones[state.id] = state;
    _stateCtrl.add(_drones.values.toList());
  }

  List<DroneState> get drones => _drones.values.toList();

  double get avgBattery {
    if (_drones.isEmpty) return 0;
    return _drones.values.map((d) => d.battery).reduce((a, b) => a + b) / _drones.length;
  }

  void dispose() => _stateCtrl.close();
}

void main() async {
  final model = FleetDashboardModel();
  final sub = model.droneStream.listen((drones) {
    print('Fleet update: ${drones.length} drones, avg battery: ${model.avgBattery.toStringAsFixed(1)}%');
  });

  model.update(DroneState(id: 'D001', lat: 37.5665, lon: 126.978, alt: 60, battery: 85, speed: 10, mode: 'AUTO'));
  model.update(DroneState(id: 'D002', lat: 37.5670, lon: 126.979, alt: 55, battery: 72, speed:  8, mode: 'AUTO'));

  await Future.delayed(Duration(milliseconds: 10));
  sub.cancel();
  model.dispose();
  print('Phase 634: Flutter Dashboard demo complete');
}
