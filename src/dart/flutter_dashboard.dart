// Flutter Dashboard — SDACS Phase 634
import 'dart:async';

class DroneStatus {
  final String id;
  final double lat;
  final double lon;
  final double alt;
  final int battery;

  DroneStatus({required this.id, required this.lat, required this.lon,
               required this.alt, required this.battery});

  Map<String, dynamic> toJson() => {
    'id': id, 'lat': lat, 'lon': lon, 'alt': alt, 'battery': battery
  };
}
