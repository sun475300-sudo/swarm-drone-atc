// Phase 555: GCS Protocol — 지상통제소 통신 프로토콜 (Dart)
// Ground Control Station protocol messages for drone telemetry and command.

import 'dart:typed_data';
import 'dart:convert';

const int PHASE = 555;
const String PROTOCOL_VERSION = 'GCS-v2.0';

// ── Message types ────────────────────────────────────────────────

enum MessageType {
  heartbeat,
  telemetry,
  command,
  ack,
  alert,
  missionItem,
}

// ── Protocol Message base ─────────────────────────────────────────

abstract class Message {
  final int sequenceId;
  final int droneId;
  final MessageType type;
  final DateTime timestamp;

  const Message({
    required this.sequenceId,
    required this.droneId,
    required this.type,
    required this.timestamp,
  });

  Map<String, dynamic> toJson();

  /// Encode message to bytes (length-prefixed JSON).
  Uint8List encode() {
    final json = jsonEncode(toJson());
    final bytes = utf8.encode(json);
    final buf = ByteData(4 + bytes.length);
    buf.setUint32(0, bytes.length, Endian.big);
    final result = buf.buffer.asUint8List();
    result.setAll(4, bytes);
    return result;
  }

  @override
  String toString() => 'Message(type: $type, drone: $droneId, seq: $sequenceId)';
}

// ── Heartbeat ─────────────────────────────────────────────────────

class HeartbeatMessage extends Message {
  final double batteryPct;
  final String status;

  const HeartbeatMessage({
    required super.sequenceId,
    required super.droneId,
    required super.timestamp,
    required this.batteryPct,
    required this.status,
  }) : super(type: MessageType.heartbeat);

  @override
  Map<String, dynamic> toJson() => {
    'type': 'heartbeat',
    'seq': sequenceId,
    'drone_id': droneId,
    'battery': batteryPct,
    'status': status,
    'ts': timestamp.millisecondsSinceEpoch,
    'protocol': PROTOCOL_VERSION,
  };
}

// ── Telemetry ─────────────────────────────────────────────────────

class TelemetryMessage extends Message {
  final double x, y, z;
  final double vx, vy, vz;
  final double heading;

  const TelemetryMessage({
    required super.sequenceId,
    required super.droneId,
    required super.timestamp,
    required this.x, required this.y, required this.z,
    required this.vx, required this.vy, required this.vz,
    required this.heading,
  }) : super(type: MessageType.telemetry);

  @override
  Map<String, dynamic> toJson() => {
    'type': 'telemetry',
    'seq': sequenceId,
    'drone_id': droneId,
    'pos': {'x': x, 'y': y, 'z': z},
    'vel': {'vx': vx, 'vy': vy, 'vz': vz},
    'heading': heading,
    'ts': timestamp.millisecondsSinceEpoch,
  };
}

// ── GCS Protocol codec ────────────────────────────────────────────

class GCSProtocol {
  int _seqCounter = 0;

  int get nextSeq => _seqCounter++;

  HeartbeatMessage buildHeartbeat(int droneId, double battery, String status) {
    return HeartbeatMessage(
      sequenceId: nextSeq,
      droneId: droneId,
      timestamp: DateTime.now(),
      batteryPct: battery,
      status: status,
    );
  }

  TelemetryMessage buildTelemetry({
    required int droneId,
    required double x, required double y, required double z,
    required double vx, required double vy, required double vz,
    required double heading,
  }) {
    return TelemetryMessage(
      sequenceId: nextSeq,
      droneId: droneId,
      timestamp: DateTime.now(),
      x: x, y: y, z: z,
      vx: vx, vy: vy, vz: vz,
      heading: heading,
    );
  }

  /// Parse a raw JSON map into a Message object.
  Message? decode(Map<String, dynamic> json) {
    switch (json['type'] as String?) {
      case 'heartbeat':
        return HeartbeatMessage(
          sequenceId: json['seq'] as int,
          droneId:    json['drone_id'] as int,
          timestamp:  DateTime.fromMillisecondsSinceEpoch(json['ts'] as int),
          batteryPct: (json['battery'] as num).toDouble(),
          status:     json['status'] as String,
        );
      default:
        return null;
    }
  }
}

// ── Entry point ───────────────────────────────────────────────────

void main() {
  print('Phase $PHASE: GCS Protocol — $PROTOCOL_VERSION 지상통제소 프로토콜');
  final gcs = GCSProtocol();

  final hb = gcs.buildHeartbeat(1, 82.5, 'flying');
  print('Heartbeat: ${hb.toJson()}');

  final telem = gcs.buildTelemetry(
    droneId: 1, x: 100.0, y: 200.0, z: 50.0,
    vx: 5.0, vy: 0.0, vz: 0.0, heading: 90.0,
  );
  print('Telemetry encoded bytes: ${telem.encode().length}');
}
