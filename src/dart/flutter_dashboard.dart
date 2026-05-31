// Phase 634 — Flutter Dashboard (Dart)
// 군집 드론 실시간 모니터링 모바일 대시보드

import 'dart:async';
import 'dart:convert';
import 'dart:math';

/// 드론 한 대의 텔레메트리 스냅샷.
class DroneSnapshot {
  final String id;
  final List<double> position;
  final List<double> velocity;
  final String phase;
  final double batteryPct;

  const DroneSnapshot({
    required this.id,
    required this.position,
    required this.velocity,
    required this.phase,
    required this.batteryPct,
  });

  factory DroneSnapshot.fromJson(Map<String, dynamic> json) => DroneSnapshot(
        id: json['id'] as String,
        position: List<double>.from(json['pos'] as List),
        velocity: List<double>.from(json['vel'] as List),
        phase: json['phase'] as String,
        batteryPct: (json['battery'] as num).toDouble(),
      );

  double get speed {
    final vx = velocity[0], vy = velocity[1], vz = velocity[2];
    return sqrt(vx * vx + vy * vy + vz * vz);
  }
}

/// WebSocket 연결로 들어오는 군집 스냅샷 스트림을 파싱한다.
class SwarmDataService {
  final String wsUrl;
  final _snapshotController = StreamController<List<DroneSnapshot>>.broadcast();

  SwarmDataService({this.wsUrl = 'ws://localhost:8765'});

  Stream<List<DroneSnapshot>> get snapshots => _snapshotController.stream;

  void processMessage(String rawJson) {
    try {
      final data = jsonDecode(rawJson) as Map<String, dynamic>;
      final drones = (data['drones'] as List)
          .map((d) => DroneSnapshot.fromJson(d as Map<String, dynamic>))
          .toList();
      _snapshotController.add(drones);
    } catch (_) {
      // 파싱 실패 무시
    }
  }

  void dispose() => _snapshotController.close();
}
