// SDACS GCS Protocol — Dart (Phase 555)
// 지상통제소(GCS) 통신 Protocol

import 'dart:async';
import 'dart:math' as math;

enum MessageType {
  heartbeat, telemetry, command, ack, alert, status
}

enum GCSCommandType {
  takeoff, land, rtl, hold, resume, setWaypoint, emergency
}

// GCS Message 기본 타입 (Phase 555)
class Message {
  final MessageType type;
  final String droneId;
  final Map<String, dynamic> payload;
  final DateTime timestamp;
  final int sequenceId;

  Message({
    required this.type,
    required this.droneId,
    required this.payload,
    required this.sequenceId,
  }) : timestamp = DateTime.now();

  Map<String, dynamic> toJson() => {
    'type': type.name,
    'drone_id': droneId,
    'payload': payload,
    'timestamp': timestamp.toIso8601String(),
    'seq': sequenceId,
  };
}

// GCS Protocol 핸들러
class GCSProtocol {
  final String stationId;
  final _controller = StreamController<Message>.broadcast();
  final _pending = <int, Completer<Message>>{};
  int _seq = 0;
  int _sent = 0;
  int _received = 0;

  GCSProtocol({required this.stationId});

  Stream<Message> get messageStream => _controller.stream;

  Message _buildMessage(MessageType type, String droneId, Map<String, dynamic> payload) {
    return Message(type: type, droneId: droneId, payload: payload, sequenceId: ++_seq);
  }

  void sendHeartbeat(String droneId) {
    final msg = _buildMessage(MessageType.heartbeat, droneId, {'station': stationId});
    _controller.add(msg);
    _sent++;
  }

  void sendCommand(String droneId, GCSCommandType cmd, [Map<String, dynamic>? params]) {
    final msg = _buildMessage(MessageType.command, droneId, {
      'command': cmd.name,
      ...?params,
    });
    _controller.add(msg);
    _sent++;
  }

  void receiveMessage(Message msg) {
    _received++;
    _controller.add(msg);
    if (msg.type == MessageType.ack) {
      final seq = msg.payload['ack_seq'] as int?;
      if (seq != null) _pending[seq]?.complete(msg);
    }
  }

  // 링크 품질 지표
  double get linkQuality {
    if (_sent == 0) return 1.0;
    return math.min(1.0, _received / _sent);
  }

  int get messageCount => _sent + _received;

  void dispose() => _controller.close();
}

// 다중 드론 GCS 관리자
class FleetGCSManager {
  final GCSProtocol protocol;
  final _droneStatus = <String, Map<String, dynamic>>{};

  FleetGCSManager({required String stationId})
      : protocol = GCSProtocol(stationId: stationId);

  void registerDrone(String droneId) {
    _droneStatus[droneId] = {'status': 'registered', 'battery': 100.0};
  }

  void updateStatus(String droneId, Map<String, dynamic> status) {
    _droneStatus[droneId] = {...?_droneStatus[droneId], ...status};
  }

  void commandAllDrones(GCSCommandType cmd) {
    for (final id in _droneStatus.keys) {
      protocol.sendCommand(id, cmd);
    }
  }

  Map<String, dynamic>? getStatus(String droneId) => _droneStatus[droneId];
  int get fleetSize => _droneStatus.length;
  List<String> get activeDrones => _droneStatus.keys.toList();
}
