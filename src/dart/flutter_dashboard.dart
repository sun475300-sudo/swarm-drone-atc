// Flutter dashboard stub for SDACS mobile/desktop UI
import 'dart:async';

class DroneStatus {
  final String id;
  final double lat, lon, alt;
  const DroneStatus(this.id, this.lat, this.lon, this.alt);
}

class DashboardController {
  final _statusStream = StreamController<List<DroneStatus>>.broadcast();
  Stream<List<DroneStatus>> get statusStream => _statusStream.stream;

  void update(List<DroneStatus> statuses) => _statusStream.add(statuses);
  void dispose() => _statusStream.close();
}
